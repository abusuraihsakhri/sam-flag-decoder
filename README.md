# SAM FLAG Decoder

A dependency-free **Sequence Alignment/Map (SAM) bitwise FLAG decoder** for single values and CSV tables. Use the browser app or the Python CLI.

The decoder follows the [SAM/BAM specification](https://github.com/samtools/hts-specs), section 1.4. It recognizes the 12 defined FLAG bits (0x1–0x800), reports reserved bits without inventing meanings, and warns when template/mate bits cannot be interpreted. A FLAG alone cannot validate an entire SAM record or mate pair.

## Browser application

The standalone app is in [web/](web/). It supports decimal and hexadecimal input, example flags, CSV paste/upload, row-wise errors, preview, and download. It uses accessible forms, responsive layouts and **local browser processing**, with no backend requests, analytics, cookies, or accounts.

To run locally:

~~~bash
python -m http.server 8000 --directory web
# Then open http://127.0.0.1:8000/
~~~

A GitHub Pages deployment workflow is included. A live URL should only be advertised after successful deployment and verification.

## Python CLI

Requires Python 3.10+. The core decoder uses only the standard library.

~~~bash
python sam_flag.py single 99
python sam_flag.py single 0x93
python sam_flag.py batch --input sample.csv --output decoded.csv
~~~

Input CSV must have headers. The decoder prefers a FLAG or sam_flag column, then query, and otherwise the first column for backward compatibility. Output preserves original fields and adds top_hit, lookup_score, flag_decimal, flag_hex, decoded_flags, warnings and error. The score counts set known bits; it **is not mapping quality**. Invalid rows receive errors; batch exit status is nonzero if any are invalid.

~~~python
from sam_flag import decode_flag, lookup, process_csv
print(decode_flag(99)["set_bits"])
print(lookup("0x93")["summary"])
process_csv("sample.csv", "decoded.csv")
~~~

## Optional legacy API and agent demonstration

The repository retains a separate FastAPI and agent-style demonstration under agents/, cli.py, and enrichment.py. This demonstration evaluates arbitrary numeric thresholds; **it does not parse SAM records or provide clinically validated decision support**. The provider factory currently returns deterministic mock responses for all provider names.

~~~bash
python -m pip install -r requirements.txt
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
python cli.py serve --host 127.0.0.1 --port 8000
~~~

The optional REST endpoints are GET /health, GET /metrics, POST /api/audit and POST /api/chat. GET /api/audit/logs is disabled without AUDIT_LOG_READ_KEY and requires an X-Audit-Read-Key header matching that variable. See [.env.example](.env.example) for settings.

Container deployment:

~~~bash
docker build -t sam-flag-decoder .
docker run --rm -p 127.0.0.1:8000:8000 -e AUDIT_SECRET_KEY="$AUDIT_SECRET_KEY" sam-flag-decoder
# Alternatively: docker compose up --build
~~~

The container runs the legacy API, not the browser app. Docker Compose refuses to start without an audit key.

## Privacy and security

The browser app processes input locally; it does not transmit uploaded CSV files, and exports are generated in-browser. Treat CSV input and output as untrusted when opening in spreadsheet programs. The optional API has pattern-based screening for certain identifiers, **not comprehensive de-identification or HIPAA compliance**. The HMAC-SHA256 audit ledger is checked for tampering but exists **only in process memory**. The API is not suitable for public exposure without additional authentication and network restrictions.

## Tests and development

~~~bash
python -m pytest -q
node --test web/app.test.mjs
python -m compileall -q sam_flag.py cli.py enrichment.py agents tests
~~~

GitHub Actions tests Python 3.10–3.12 and browser JavaScript. Modern browsers with ES modules are supported. No Pyodide is needed: the browser implementation uses JavaScript to compute bit masks.

## License

[MIT](LICENSE).
