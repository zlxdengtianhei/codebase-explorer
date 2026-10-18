# Configuration Loading

**Capability.** Owns the Config dict and its loaders: Python files, objects, mappings, environment variables and prefixed env vars, plus namespace queries and the ConfigAttribute descriptor forwarding App attributes to config.

Use this to learn every supported way to populate app config and how keys are filtered (uppercase only). The instance-path tests cover how the app locates its instance folder for installed and uninstalled packages.

**Depends on.**

- [Testing Support](r2-testing-support.md) · graph-confirmed · 7 edge(s) · Instance-path configuration tests rely on shared conftest fixtures.
- [Functional Behavior Tests](r1-tests-functional.md) · graph-only · 1 edge(s)

**Depended on by.**

- [CLI Test Suite](r2-cli-tests.md) · model-inferred · 0 edge(s)
- [JSON Test Suite](r2-json-tests.md) · model-inferred · 0 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (10)

<a id="u-ac0761560ac0"></a>
### `config.py-configattribute`

`class ConfigAttribute(t.Generic[T]):` · [src/flask/config.py:L20-L23][f1]

A generic descriptor that forwards attribute access on an App to its config dictionary.

__init__ stores the config key name and an optional converter callable. __get__ returns the descriptor itself when accessed on the class (obj is None); otherwise it looks up obj.config[self.__name__] and applies get_converter if one was supplied. __set__ writes the value into obj.config under the stored name. Missing keys surface as ordinary dict KeyError from the config lookup.

uses: [Config](r2-configuration.md#u-61ff4c22bbf1)

**Uncertainties.**

- Whether get_converter errors are caught anywhere is not visible in this file.

<a id="u-61ff4c22bbf1"></a>
### `Config`

`class Config(dict): # type: ignore[type-arg]` · [src/flask/config.py:L50-L94][f1]

A dict subclass that adds loaders for populating configuration from files, objects, environment variables, and mappings.

__init__ seeds the dict with defaults (or an empty dict) and stores root_path, which all file-based loaders join relative paths against. from_object copies only attributes whose names are entirely uppercase; the same uppercase filter applies in from_mapping. The class docstring documents the intended usage patterns and that lowercase keys are skipped so files can hold temporary values.

<a id="u-b792d0a20697"></a>
### `Config.from_envvar`

`def from_envvar(self, variable_name: str, silent: bool = False) -> bool:` · [src/flask/config.py:L102-L124][f1]

Loads config from a file named by an environment variable.

If the variable is unset or empty and silent is True it returns False; otherwise it raises RuntimeError naming the variable. If set, it delegates to from_pyfile with the variable's value and the same silent flag, returning that method's bool result.

calls: [Config.from_pyfile](r2-configuration.md#u-c4736c8beba8)

<a id="u-4131a01c47fc"></a>
### `Config.from_file`

`def from_file( self, filename: str | os.PathLike[str], load: t.Callable[[t.IO[t.Any]]…` · [src/flask/config.py:L256-L302][f1]

Loads config from a file using a caller-supplied loader callable.

The filename is joined against root_path and opened in text mode unless text is False, in which case binary mode is used; load receives the file handle and must return a mapping, which is passed to from_mapping. On OSError: if silent is True and errno is ENOENT or EISDIR it returns False; otherwise e.strerror is rewritten to 'Unable to load configuration file (...)' and the error re-raises. Exceptions raised by load itself are not caught here.

calls: [Config.from_mapping](r2-configuration.md#u-2e2d482fcf30)

**Uncertainties.**

- Graph shows load(f) resolves to two candidates (flask.json.load or JSONProvider.load); which callable is used depends on the caller-supplied argument.
- ENOTDIR is absent from the silent errno list here, unlike from_pyfile.

<a id="u-2e2d482fcf30"></a>
### `Config.from_mapping`

`def from_mapping( self, mapping: t.Mapping[str, t.Any] | None = None, **kwargs: t.Any…` · [src/flask/config.py:L304-L321][f1]

Updates the config from an optional mapping plus keyword arguments, keeping only keys whose names are entirely uppercase.

kwargs override the mapping on conflicts. Always returns True regardless of what was loaded.

<a id="u-b07075178acd"></a>
### `Config.from_object`

`def from_object(self, obj: object | str) -> None:` · [src/flask/config.py:L218-L254][f1]

Copies uppercase attributes from an object into the config.

If obj is a string it is first resolved with import_string; resolution errors propagate. It iterates dir(obj) and assigns each attribute whose name is entirely uppercase via getattr, so class attributes (not dict items) are loaded and property objects are copied un-evaluated. Returns None and mutates the config in place.

uses: [Config](r2-configuration.md#u-61ff4c22bbf1)

<a id="u-3ea8469172b0"></a>
### `Config.from_prefixed_env`

`def from_prefixed_env( self, prefix: str = "FLASK", *, loads: t.Callable[[str], t.Any…` · [src/flask/config.py:L126-L185][f1]

Loads every environment variable starting with the given prefix plus an underscore (default 'FLASK_'), stripping the prefix to form the config key.

Keys are processed in sorted os.environ order. Each value is passed through loads (default json.loads); if loads raises any Exception the original string is kept. Keys without '__' are set directly; keys containing '__' are split on '__' and traverse nested dicts, creating empty dicts for missing intermediate keys before setting the tail key. Always returns True, including when nothing matched.

**Uncertainties.**

- Nested traversal does not validate that an existing intermediate value is a dict; assigning into a non-dict would raise, and handling of that error is not visible here.

<a id="u-c4736c8beba8"></a>
### `Config.from_pyfile`

`def from_pyfile( self, filename: str | os.PathLike[str], silent: bool = False ) -> bool:` · [src/flask/config.py:L187-L216][f1]

Executes a Python file and loads its uppercase attributes via from_object.

The filename is joined against root_path. The file is compiled and exec'd into a fresh module namespace whose __file__ is set to the path. On OSError: if silent is True and errno is ENOENT, EISDIR, or ENOTDIR it returns False; otherwise it rewrites e.strerror to 'Unable to load configuration file (...)' and re-raises. On success it calls from_object on the module and returns True. Errors raised inside the executed file propagate unmodified.

calls: [Config.from_object](r2-configuration.md#u-b07075178acd); uses: [Config](r2-configuration.md#u-61ff4c22bbf1)

**Uncertainties.**

- Only OSError is handled; a missing-but-unreadable path with a different errno is not covered by the silent list.

<a id="u-619af47ae8b6"></a>
### `Config.get_namespace`

`def get_namespace( self, namespace: str, lowercase: bool = True, trim_namespace: bool…` · [src/flask/config.py:L323-L364][f1]

Returns a dict of config entries whose keys start with the given namespace prefix.

For each match, trim_namespace (default True) strips the prefix and lowercase (default True) lowercases the remaining key; values are copied unchanged. Non-matching keys are skipped and the config itself is not modified.

<a id="u-e7aabf40bbdd"></a>
### `test_instance_config.py-instance-paths`

`def test_explicit_instance_paths(modules_tmp_path):` · [tests/test_instance_config.py:L8-L13][f2]

Tests that Flask computes app.instance_path from the importing module's location for installed and uninstalled modules, packages, and namespace packages.

test_explicit_instance_paths: a relative instance_path raises ValueError matching 'must be absolute', while an absolute path is used verbatim. The uninstalled tests write minimal apps (module file, package __init__, or namespace packages created under project directories prepended to sys.path) into a temp modules dir and assert instance_path is <modules_tmp>/instance — i.e. derived from the source location. The installed tests place apps under a fake site-packages with sys.prefix pointed at the modules dir and assert instance_path becomes <prefix>/var/<name>-instance; test_prefix_package_paths repeats this for a package living inside site-packages. Each test uses the purge_module fixture to schedule popping the imported app module so subsequent imports re-execute. The matrix: source under the temp (uninstalled) root -> <root>/instance; source under an installed root (site-packages/prefix-aware) -> <prefix>/var/<name>-instance.

uses: [conftest.py-fixtures](r2-testing-support.md#u-7a1aa125604a); group: [test_instance_config.py-instance-paths](r2-configuration.md#u-e7aabf40bbdd)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/config.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/test_instance_config.py
