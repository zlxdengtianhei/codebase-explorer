# Walkthrough videos

## Flask's own code, narrated (2 minutes)

One request through Flask: `wsgi_app` pushes the request context, `full_dispatch_request` runs the before-request hooks and the view, `make_response` and `process_response` build the response, and the contexts pop. Then what the application and request contexts hold, how the `current_app` and `request` proxies find them, how blueprints defer registration, and how configuration is loaded. Each sentence cites a unit explanation in [examples/flask](../examples/flask/docs/INDEX.md) and the Flask source lines it rests on; the code on screen is that source, with the lines the sentence is about highlighted.

- Watch: https://github.com/user-attachments/assets/87b5b1c1-452e-48e0-af29-2e520391093a
- The voice is synthetic (Kokoro-82M, Apache-2.0). Script: [`showcase/tour/codefilm.en.json`](../showcase/tour/codefilm.en.json); rebuild with [`showcase/make_codefilm.sh`](../showcase/make_codefilm.sh).

## Narrated walkthrough, Flask (2 minutes)

It follows Flask from source files to the module map, visits the eight top-level modules one by one, opens one module page, and shows `cbe find` and `cbe source`. It was recorded from the program-built tree; every number, module name and command output on screen comes from the generated catalog.

- Watch it in the browser, with the transcript in English and Chinese: [narrated walkthrough](https://zlxdengtianhei.github.io/codebase-explorer/film.html)
- File: [walkthrough-flask-1.mp4](https://github.com/zlxdengtianhei/codebase-explorer/releases/download/walkthrough-v2.2.0.dev0/walkthrough-flask-1.mp4)
- The voice is synthetic (Kokoro-82M, Apache-2.0). The script, the recorder and the narration data are in [`showcase/`](../showcase/README.md).
