# Domain Research: Module Upload Progress Feedback

## FastAPI Streaming Responses (StreamingResponse)
FastAPI provides `StreamingResponse` to stream chunked payloads over HTTP using standard generators. By yielding newline-delimited JSON strings (`application/x-ndjson`), we can push structured progression logs directly to the browser.
- **Reference**: FastAPI/Starlette response handling guidelines (Starlette documentation).
- **Cons**: Connection must remain open, requiring client-side streaming consumption.

## React & browser ReadableStream API
Modern browsers support processing streaming response bodies directly via `fetch` and `response.body.getReader()`. This allows a React state loop to continuously read incoming text chunks, decode them as UTF-8, split by newline, parse them as JSON, and sequentially transition progress bars or checklists in the UI.
- **Reference**: Streams API - Web APIs | MDN.
- **Cons**: Requires custom stream parser loop in client component (since React Query's default JSON fetchers assume single resolved promises).
