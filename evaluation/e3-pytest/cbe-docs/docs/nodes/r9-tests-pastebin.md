# Pastebin Test Suite

**Capability.** Tests of the --pastebin failure-report integration: end-to-end capture of failure reports and unit tests of create_new_paste against mocked urllib behavior.

Use this to see both the integration contract and the network-request unit coverage (URL construction, error handling).

Parent: [pytest Core](r9-pytest-core.md)

## Units (2)

<a id="u-17f41615e1b1"></a>
### `test-pastebin-paste-capture`

`class TestPasteCapture:` · [testing/test_pastebin.py:L13-L14][f1]

Tests the --pastebin failure-report integration.

The pastebinlist fixture looks up the registered 'pastebin' plugin and monkeypatches its create_new_paste with list.append, so each paste attempt records its payload in the returned list. With --pastebin=failed on a run of one pass, one failure and one skip, exactly one paste is created whose contents contain 'def test_fail', and outcomes are [1, 1, 1]. With --pastebin=all and -v, the pasted (utf-8 decoded) report contains per-test PASSED/FAILED/SKIPPED lines and the '1 failed, 1 passed, 1 skipped' summary. With non-ascii assertion text ('☺' == 1), the terminal report shows the assertion, the failure summary, and 'Sending information to Paste Service', and exactly one paste is made — non-ascii survives the round trip (#1219).

uses: [_pytest.monkeypatch](../../catalog.json); calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-8729d0fbbfed"></a>
### `test-pastebin-paste-plugin`

`class TestPaste:` · [testing/test_pastebin.py:L89-L90][f1]

Tests the pastebin plugin's create_new_paste against mocked urllib behavior.

The mocked_urlopen fixtures monkeypatch urllib.request.urlopen with a function recording (url, data) calls and returning a DummyFile whose read yields canned response bytes; the valid fixture returns a normal bpaste response fragment containing '/raw/3c0c6750bd', the invalid fixture returns '/invalid/3c0c6750bd'. Established behavior: a well-formed response produces the URL 'https://bpa.st/show/3c0c6750bd' and exactly one POST to 'https://bpa.st' whose body is bytes containing lexer=text, code=full-paste-contents and expiry=1week. A response whose link does not match the expected format yields the string 'bad response: invalid format (<response text>)'. An HTTPError(400, 'Bad request') side effect yields 'bad response: HTTP Error 400: Bad request'; a URLError yields 'bad response: <urlopen error the url was bad>'. A plain BytesIO response with unrelated content also yields the invalid-format message.

uses: [_pytest.monkeypatch](../../catalog.json); calls: [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pastebin.py
