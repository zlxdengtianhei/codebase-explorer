# Configuration Tests

**Capability.** tests/test_config.py: loading config from objects, classes, modules, py-files (multiple encodings), mappings, environment variables, JSON/TOML files, and prefixed env vars with nesting; get_namespace filtering, custom Config subclasses, missing-file error and silent behavior, and the PERMANENT_SESSION_LIFETIME timedelta conversion.

Use this module as the spec for every Config loading path and its error/silent semantics. common_object_test is the shared assertion each loader test runs after loading.

Parent: [Test Suites and Fixture Apps](r1-tests.md)

## Units (19)

<a id="u-cc9fdc626eab"></a>
### `test_config.py module code (L1–L12)`

`module_region` · [tests/test_config.py:L1-L12][f1]

Imports json, os, pytest, flask and defines module-level TEST_KEY and SECRET_KEY constants, which from_pyfile/from_object tests load into app config.

<a id="u-8a98bd15642e"></a>
### `common_object_test`

`def common_object_test(app):` · [tests/test_config.py:L13-L16][f1]

Shared assertions verifying a config was loaded: secret key is 'config', TEST_KEY is 'foo', and the module object itself was not added under its class name.

No branching or failure paths.

uses: [test_config_from_pyfile](r1-tests-config.md#u-e88231184a00)

<a id="u-e88231184a00"></a>
### `test_config_from_pyfile`

`def test_config_from_pyfile():` · [tests/test_config.py:L19-L22][f1]

Loads configuration from the sibling .py file derived from this test module's name (replacing the extension with '.py'), then asserts the loaded values via common_object_test.

calls: [common_object_test](r1-tests-config.md#u-8a98bd15642e)

**Uncertainties.**

- Behavior of Config.from_pyfile itself is not in this file

<a id="u-472d75803ff4"></a>
### `test_config_from_object`

`def test_config_from_object():` · [tests/test_config.py:L25-L28][f1]

Loads configuration from the module object named by this test module via from_object(__name__), then asserts the shared expectations with common_object_test.

calls: [common_object_test](r1-tests-config.md#u-8a98bd15642e)

<a id="u-e42e83ec7f83"></a>
### `test_config_from_class`

`def test_config_from_class():` · [tests/test_config.py:L132-L133][f1]

Verifies from_object inherits class attributes: Base defines TEST_KEY, subclass Test adds SECRET_KEY, and loading Test yields both values per common_object_test.

calls: [common_object_test](r1-tests-config.md#u-8a98bd15642e)

<a id="u-f62e9d5372e7"></a>
### `test_config_from_mapping`

`def test_config_from_mapping():` · [tests/test_config.py:L110-L129][f1]

Exercises from_mapping with four input shapes: a dict, a list of key/value tuples, keyword arguments, and keywords plus an extra key (which is still loaded without complaint).

Finally asserts that calling from_mapping({}, {}) — two positional mappings — raises TypeError.

**Notes.**

- failure: Two positional mapping arguments are rejected with TypeError

<a id="u-a31b66dfd88e"></a>
### `test_config_from_envvar`

`def test_config_from_envvar(monkeypatch):` · [tests/test_config.py:L144-L158][f1]

Checks from_envvar in three states with os.environ replaced by monkeypatch: unset name raises RuntimeError whose message contains "'FOO_SETTINGS' is not set"; with silent=True the same condition returns False instead of raising; when the variable names this test module's sibling .py file, it returns True and the loaded config passes common_object_test.

**Notes.**

- condition: silent=True converts the missing-variable error into a False return
- failure: RuntimeError message includes the quoted variable name

<a id="u-8fa6e9d6ef07"></a>
### `test_config_from_envvar_missing`

`def test_config_from_envvar_missing(monkeypatch):` · [tests/test_config.py:L161-L171][f1]

With FOO_SETTINGS pointing at the nonexistent 'missing.cfg', from_envvar raises IOError whose message starts with '[Errno 2] Unable to load configuration file' and ends with the file name; silent=True returns False instead.

<a id="u-e5b8b4c3a210"></a>
### `test_config_from_file_json`

`def test_config_from_file_json():` · [tests/test_config.py:L31-L35][f1]

Loads <test dir>/static/config.json with json.load via Config.from_file and asserts the shared values using common_object_test.

calls: [common_object_test](r1-tests-config.md#u-8a98bd15642e)

<a id="u-502d34c622fb"></a>
### `test_config_from_file_toml`

`def test_config_from_file_toml():` · [tests/test_config.py:L38-L45][f1]

Skips the test when tomllib is unavailable (Python < 3.11), loads static/config.toml with tomllib.load and text=False, then verifies shared values via common_object_test.

calls: [common_object_test](r1-tests-config.md#u-8a98bd15642e)

<a id="u-701fb2dcf6ca"></a>
### `test_config_missing`

`def test_config_missing():` · [tests/test_config.py:L174-L183][f1]

from_pyfile on 'missing.cfg' raises IOError with the standard 'Unable to load configuration file' message ending in the filename; silent=True suppresses the error and returns False.

<a id="u-dd4f1a57ecfb"></a>
### `test_config_missing_file`

`def test_config_missing_file():` · [tests/test_config.py:L186-L195][f1]

from_file('missing.json', json.load) raises IOError with the same load-failure message format; silent=True returns False instead of raising.

<a id="u-5ebe3959e3d7"></a>
### `test_custom_config_class`

`def test_custom_config_class():` · [tests/test_config.py:L198-L199][f1]

Subclasses flask.Config as Config and flask.Flask as Flask with config_class = Config; asserts the app instance uses the custom Config type and that loading this module populates the shared values.

calls: [common_object_test](r1-tests-config.md#u-8a98bd15642e)

<a id="u-0bfa3dbc3ace"></a>
### `test_from_prefixed_env`

`def test_from_prefixed_env(monkeypatch):` · [tests/test_config.py:L48-L66][f1]

Verifies from_prefixed_env() with the default FLASK_ prefix: string, bool ('true' → True), int, float, JSON list and JSON dict env vars become typed config keys, while non-prefixed NOT_FLASK_OTHER is ignored.

Values are set with monkeypatch so no real environment is touched.

**Uncertainties.**

- Parsing rules live in Config.from_prefixed_env, not shown here

<a id="u-3e3f9cbc2bae"></a>
### `test_from_prefixed_env_custom_prefix`

`def test_from_prefixed_env_custom_prefix(monkeypatch):` · [tests/test_config.py:L69-L76][f1]

Passes 'NOT_FLASK' as a custom prefix to from_prefixed_env, asserting that NOT_FLASK_A='b' (not FLASK_A='a') is loaded into config key A.

<a id="u-da6f335bc003"></a>
### `test_from_prefixed_env_nested`

`def test_from_prefixed_env_nested(monkeypatch):` · [tests/test_config.py:L79-L107][f1]

Verifies double-underscore nesting in from_prefixed_env.

Pre-seeds config EXIST with nested keys, then loads FLASK_EXIST__ok, FLASK_EXIST__inner__ik (overwriting nested value 1→2), FLASK_EXIST__new__more (JSON dict), and FLASK_NEW__K. On non-Windows, EXIST merges into the existing dict producing the fully merged structure; on Windows the branch asserts that because env var names are uppercased, nested keys arrive as OK, INNER, NEW, MORE rather than lowercase, leaving original lowercase keys intact. NEW is loaded fresh as {'K': 'v'} on all platforms.

**Notes.**

- condition: os.name == 'nt' selects a separate assertion branch reflecting uppercased Windows env keys
- side_effect: from_prefixed_env mutates the pre-existing EXIST mapping in place on non-Windows, preserving the 'flag' key

**Uncertainties.**

- In-place mutation semantics are inferred from the asserted merged result, not from loader source

<a id="u-87d0e8651ac5"></a>
### `test_from_pyfile_weird_encoding`

`def test_from_pyfile_weird_encoding(tmp_path, encoding):` · [tests/test_config.py:L243-L250][f1]

Parametrized over utf-8, iso-8859-15, and latin-1: writes a config .py declaring its coding cookie and a non-ASCII TEST_VALUE, loads it with from_pyfile, and asserts the decoded string equals 'föö'.

<a id="u-65f366e7b6d9"></a>
### `test_get_namespace`

`def test_get_namespace():` · [tests/test_config.py:L217-L240][f1]

Verifies Config.get_namespace option filtering with four variants: default call returns lowercase keys with the namespace prefix trimmed (option_1, option_2); lowercase=False keeps original case (STUFF_1); trim_namespace=False retains the prefix (foo_option_1); both flags off gives BAR_STUFF_1.

Each call returns exactly the two FOO_/BAR_ entries.

**Notes.**

- contract: Only keys beginning with the namespace prefix are returned

<a id="u-10bbe6364ec6"></a>
### `test_session_lifetime`

`def test_session_lifetime():` · [tests/test_config.py:L211-L214][f1]

Setting config key PERMANENT_SESSION_LIFETIME to the integer 42 is reflected by app.permanent_session_lifetime.seconds == 42, showing the property converts config values to timedeltas.

**Uncertainties.**

- Conversion logic lives outside this file

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_config.py
