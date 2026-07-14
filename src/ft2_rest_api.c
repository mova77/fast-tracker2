#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#ifndef _WIN32
#include <unistd.h>
#endif
#include <microhttpd.h>
#include "ft2_renderer.h"

static volatile sig_atomic_t serverKeepRunning = 1;

static void serverSignalHandler(int sig)
{
	(void)sig;
	serverKeepRunning = 0;
}

#define REST_API_PORT 8080
#define MAX_UPLOAD_SIZE (50 * 1024 * 1024)  /* 50MB max file size */
#define TMP_DIR "/tmp/ft2-api"

/* renamed in newer libmicrohttpd; keep building against both */
#ifndef MHD_HTTP_CONTENT_TOO_LARGE
#define MHD_HTTP_CONTENT_TOO_LARGE MHD_HTTP_PAYLOAD_TOO_LARGE
#endif

/* per-connection upload buffer (POST body is delivered in chunks) */
typedef struct {
	char  *data;
	size_t size;
	size_t capacity;
} conn_ctx_t;

/* Simple JSON builder - no external dependencies */
static char *build_json_response(const char *status, const char *message)
{
	size_t size = 512;
	char *json = malloc(size);
	if (!json) return NULL;

	snprintf(json, size, "{"
		"\"status\": \"%s\","
		"\"message\": \"%s\""
		"}", status, message);
	
	return json;
}

static char *build_json_render_result(const render_result_t *result,
	const char *filename)
{
	size_t size = 1024;
	char *json = malloc(size);
	if (!json) return NULL;

	if (result->success) {
		snprintf(json, size, "{"
			"\"status\": \"success\","
			"\"filename\": \"%s\","
			"\"samples\": %u,"
			"\"duration_seconds\": %.2f,"
			"\"download_url\": \"/api/download/%s\""
			"}", 
			filename,
			result->total_samples,
			result->duration_ms / 1000.0f,
			filename);
	} else {
		snprintf(json, size, "{"
			"\"status\": \"error\","
			"\"error\": \"%s\""
			"}", 
			render_error_to_string(result));
	}

	return json;
}

/* Health check endpoint */
static enum MHD_Result handle_health(struct MHD_Connection *connection)
{
	const char *response = "{\"status\": \"ok\", \"version\": \"1.0\"}";
	struct MHD_Response *mhd_response = MHD_create_response_from_buffer(
		strlen(response),
		(void *)response,
		MHD_RESPMEM_PERSISTENT
	);

	MHD_add_response_header(mhd_response, "Content-Type", "application/json");
	MHD_queue_response(connection, MHD_HTTP_OK, mhd_response);
	MHD_destroy_response(mhd_response);
	return MHD_YES;
}

/* send a JSON string as the response (frees json) */
static enum MHD_Result send_json(struct MHD_Connection *connection,
	unsigned int http_status, char *json)
{
	if (json == NULL) {
		const char *error = "{\"status\": \"error\", \"error\": \"Memory allocation failed\"}";
		struct MHD_Response *r = MHD_create_response_from_buffer(
			strlen(error), (void *)error, MHD_RESPMEM_PERSISTENT);
		MHD_add_response_header(r, "Content-Type", "application/json");
		MHD_queue_response(connection, MHD_HTTP_INTERNAL_SERVER_ERROR, r);
		MHD_destroy_response(r);
		return MHD_YES;
	}

	struct MHD_Response *r = MHD_create_response_from_buffer(
		strlen(json), (void *)json, MHD_RESPMEM_MUST_FREE);
	MHD_add_response_header(r, "Content-Type", "application/json");
	MHD_queue_response(connection, http_status, r);
	MHD_destroy_response(r);
	return MHD_YES;
}

/* read an unsigned integer query-string argument, or return the fallback */
static uint32_t query_uint(struct MHD_Connection *connection,
	const char *key, uint32_t fallback)
{
	const char *v = MHD_lookup_connection_value(connection, MHD_GET_ARGUMENT_KIND, key);
	if (v == NULL || v[0] == '\0')
		return fallback;

	long n = strtol(v, NULL, 10);
	if (n < 0)
		n = 0;

	return (uint32_t)n;
}

/*
 * Render endpoint: POST /api/render
 *
 * The request body is the raw module file (e.g. `curl --data-binary @song.mod`).
 * Optional query params: ?rate=48000&bits=16&amp=16&start=0&stop=255
 *
 * MHD delivers the body across multiple calls, so we accumulate it in a
 * per-connection context and only render once the full body has arrived.
 */
static enum MHD_Result handle_render(struct MHD_Connection *connection,
	const char *upload_data, size_t *upload_data_size, void **con_cls)
{
	static unsigned int renderCounter = 0; /* daemon is single-threaded (see below) */

	conn_ctx_t *ctx = (conn_ctx_t *)*con_cls;

	/* first call for this connection: allocate the accumulation buffer */
	if (ctx == NULL) {
		ctx = (conn_ctx_t *)calloc(1, sizeof (conn_ctx_t));
		if (ctx == NULL)
			return MHD_NO;

		*con_cls = ctx;
		return MHD_YES; /* wait for the body */
	}

	/* body chunk: append to the buffer */
	if (*upload_data_size > 0) {
		const size_t newSize = ctx->size + *upload_data_size;
		if (newSize > MAX_UPLOAD_SIZE)
			return send_json(connection, MHD_HTTP_CONTENT_TOO_LARGE,
				build_json_response("error", "Uploaded file exceeds 50MB limit"));

		if (newSize > ctx->capacity) {
			size_t cap = (ctx->capacity == 0) ? (1 << 16) : ctx->capacity;
			while (cap < newSize)
				cap <<= 1;

			char *p = (char *)realloc(ctx->data, cap);
			if (p == NULL)
				return MHD_NO;

			ctx->data = p;
			ctx->capacity = cap;
		}

		memcpy(ctx->data + ctx->size, upload_data, *upload_data_size);
		ctx->size = newSize;
		*upload_data_size = 0;
		return MHD_YES;
	}

	/* final call: the whole body has been received */
	if (ctx->size == 0)
		return send_json(connection, MHD_HTTP_BAD_REQUEST,
			build_json_response("error", "Empty request body (send the module as raw POST data)"));

	render_config_t config;
	config.sample_rate   = query_uint(connection, "rate",  44100);
	config.bit_depth     = (uint8_t)query_uint(connection, "bits",  16);
	config.amplification = (int16_t)query_uint(connection, "amp",   16);
	config.start_pos     = (uint8_t)query_uint(connection, "start", 0);
	config.stop_pos      = (uint8_t)query_uint(connection, "stop",  255);
	config.max_loops     = (uint16_t)query_uint(connection, "loops", 1);

	const unsigned int id = ++renderCounter;

	char inPath[512], outName[64], outPath[512];
	snprintf(inPath,  sizeof(inPath),  "%s/upload_%u.mod", TMP_DIR, id);
	snprintf(outName, sizeof(outName), "render_%u.wav", id);
	snprintf(outPath, sizeof(outPath), "%s/%s", TMP_DIR, outName);

	FILE *f = fopen(inPath, "wb");
	if (f == NULL)
		return send_json(connection, MHD_HTTP_INTERNAL_SERVER_ERROR,
			build_json_response("error", "Could not write uploaded file to disk"));

	fwrite(ctx->data, 1, ctx->size, f);
	fclose(f);

	render_result_t result = render_mod_to_wav(inPath, outPath, config);
	remove(inPath); /* the WAV is kept for /api/download; drop the input */

	return send_json(connection, result.success ? MHD_HTTP_OK : MHD_HTTP_BAD_REQUEST,
		build_json_render_result(&result, outName));
}

/* free the per-connection upload buffer when the request finishes */
static void request_completed(void *cls, struct MHD_Connection *connection,
	void **con_cls, enum MHD_RequestTerminationCode toe)
{
	(void)cls; (void)connection; (void)toe;

	conn_ctx_t *ctx = (conn_ctx_t *)*con_cls;
	if (ctx != NULL) {
		free(ctx->data);
		free(ctx);
		*con_cls = NULL;
	}
}

/* Main request handler */
static enum MHD_Result request_handler(void *cls,
	struct MHD_Connection *connection,
	const char *url,
	const char *method,
	const char *version,
	const char *upload_data,
	size_t *upload_data_size,
	void **con_cls)
{
	(void)cls;
	(void)version;

	printf("[%s] %s\n", method, url);

	/* Route: GET /api/health */
	if (strcmp(url, "/api/health") == 0 && strcmp(method, "GET") == 0) {
		return handle_health(connection);
	}

	/* Route: POST /api/render */
	if (strcmp(url, "/api/render") == 0 && strcmp(method, "POST") == 0) {
		return handle_render(connection, upload_data, upload_data_size, con_cls);
	}

	/* Route: GET /api/download/:filename */
	if (strncmp(url, "/api/download/", 14) == 0 && strcmp(method, "GET") == 0) {
		const char *filename = url + 14;
		char filepath[512];
		snprintf(filepath, sizeof(filepath), "%s/%s", TMP_DIR, filename);

		FILE *f = fopen(filepath, "rb");
		if (!f) {
			const char *error = "{\"status\": \"error\", \"error\": \"File not found\"}";
			struct MHD_Response *response = MHD_create_response_from_buffer(
				strlen(error), (void *)error, MHD_RESPMEM_PERSISTENT
			);
			MHD_queue_response(connection, MHD_HTTP_NOT_FOUND, response);
			MHD_destroy_response(response);
			return MHD_YES;
		}

		fseek(f, 0, SEEK_END);
		size_t filesize = ftell(f);
		fseek(f, 0, SEEK_SET);

		void *filebuffer = malloc(filesize);
		if (!filebuffer) {
			fclose(f);
			const char *error = "{\"status\": \"error\", \"error\": \"Memory allocation failed\"}";
			struct MHD_Response *response = MHD_create_response_from_buffer(
				strlen(error), (void *)error, MHD_RESPMEM_PERSISTENT
			);
			MHD_queue_response(connection, MHD_HTTP_INTERNAL_SERVER_ERROR, response);
			MHD_destroy_response(response);
			return MHD_YES;
		}

		fread(filebuffer, 1, filesize, f);
		fclose(f);

		struct MHD_Response *response = MHD_create_response_from_buffer(
			filesize, filebuffer, MHD_RESPMEM_MUST_FREE
		);
		MHD_add_response_header(response, "Content-Type", "audio/wav");
		MHD_queue_response(connection, MHD_HTTP_OK, response);
		MHD_destroy_response(response);
		return MHD_YES;
	}

	/* Route: Not Found */
	const char *not_found = "{\"status\": \"error\", \"error\": \"Endpoint not found\"}";
	struct MHD_Response *response = MHD_create_response_from_buffer(
		strlen(not_found), (void *)not_found, MHD_RESPMEM_PERSISTENT
	);
	MHD_queue_response(connection, MHD_HTTP_NOT_FOUND, response);
	MHD_destroy_response(response);
	return MHD_YES;
}

int handle_rest_api_mode(int argc, char *argv[])
{
	int port = REST_API_PORT;

	/* Parse optional port argument: argv layout is [0]=binary [1]=--server [2]=port */
	if (argc > 2) {
		port = atoi(argv[2]);
		if (port < 1024 || port > 65535) {
			fprintf(stderr, "Error: Port must be between 1024 and 65535\n");
			return 1;
		}
	}

	/* Create temp directory if needed */
	system("mkdir -p " TMP_DIR);

	printf("Starting ft2-api REST server on port %d...\n", port);
	printf("  Health check:  GET http://localhost:%d/api/health\n", port);
	printf("  Render MOD:    POST http://localhost:%d/api/render\n", port);
	printf("  Download WAV:  GET http://localhost:%d/api/download/<filename>\n", port);
	printf("\nPress Ctrl+C to stop.\n\n");

	/* Start HTTP server.
	 * Single internal polling thread: the FT2 replayer/mixer uses global state
	 * and is NOT thread-safe, so renders must be handled one at a time. */
	struct MHD_Daemon *daemon = MHD_start_daemon(
		MHD_USE_INTERNAL_POLLING_THREAD,
		port,                   /* Port */
		NULL,                   /* Accept policy callback */
		NULL,                   /* Accept policy callback data */
		&request_handler,       /* Request handler */
		NULL,                   /* Request handler data */
		MHD_OPTION_NOTIFY_COMPLETED, &request_completed, NULL,
		MHD_OPTION_END
	);

	if (!daemon) {
		fprintf(stderr, "Error: Failed to start HTTP daemon\n");
		return 1;
	}

	printf("Server started successfully!\n");

	/* Run until interrupted (SIGINT/SIGTERM). The daemon serves requests on its
	 * own thread; block here until a shutdown signal arrives. We can't rely on
	 * getchar() because stdin may be closed/redirected in headless deployments. */
	signal(SIGINT, serverSignalHandler);
	signal(SIGTERM, serverSignalHandler);

	printf("Waiting for requests (Ctrl+C to exit)...\n");
	while (serverKeepRunning)
	{
#ifdef _WIN32
		Sleep(200);
#else
		usleep(200 * 1000);
#endif
	}

	MHD_stop_daemon(daemon);
	printf("\nServer stopped.\n");

	return 0;
}
