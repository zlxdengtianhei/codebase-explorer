# Configuration Loading

**Capability.** Implements the Config dict and its loaders from Python files, objects, mappings, data files and environment variables, plus a config-backed attribute descriptor.

Come here to learn how app configuration is stored and populated. It includes Config, its from_* loading methods, namespace extraction and the ConfigAttribute descriptor.

Parent: [Flask Web Framework](flask-web-framework.md)

## Units (14)

<a id="u-c40de09d12f2"></a>
### `config.py-configattribute-get`

`def __get__(self, obj: None, owner: None) -> te.Self:` · [src/flask/config.py:L29-L30][f1]

Descriptor read.

The first two definitions are typing overloads only.
When accessed on the class (obj is None), returns the descriptor. Otherwise returns obj.config[name], raising KeyError if the key is absent, and passes the value through get_converter when one is set (converter errors propagate; None values are also converted).

<a id="u-61ff4c22bbf1"></a>
### `Config`

`class Config(dict): # type: ignore[type-arg]` · [src/flask/config.py:L50-L94][f1]

A dict subclass that holds application configuration and can be filled from Python files, objects, mappings, structured files, or environment variables.

It adds a root_path for resolving relative filenames; only uppercase keys are accepted by the from_* loaders (except from_prefixed_env, which does not filter by case).

inherits: [dict](../../catalog.json.gz)

<a id="u-79758e5e60e2"></a>
### `ConfigAttribute`

`class ConfigAttribute(t.Generic[T]):` · [src/flask/config.py:L20-L23][f1]

Descriptor that exposes an application attribute backed by a config entry.

It is generic over the converted value type. On a class access it returns itself; on an instance access it reads obj.config[name], optionally through get_converter. Assignment writes through to obj.config[name] with no conversion.

<a id="u-1796304238ca"></a>
### `Config.__init__`

`def __init__( self, root_path: str | os.PathLike[str], defaults: dict[str, t.Any] | N…` · [src/flask/config.py:L94-L100][f1]

Initializes the dict with the given defaults (empty if None or falsy) and records root_path used to resolve relative filenames.

<a id="u-e51f74e73f76"></a>
### `Config.__repr__`

`def __repr__(self) -> str:` · [src/flask/config.py:L366-L367][f1]

Returns a representation of the form '<ClassName {dict contents}>', using the dict repr and the actual subclass name.

<a id="u-b792d0a20697"></a>
### `Config.from_envvar`

`def from_envvar(self, variable_name: str, silent: bool = False) -> bool:` · [src/flask/config.py:L102-L124][f1]

Loads configuration from a Python file whose path is stored in an environment variable.

If the variable is unset or empty: with silent=True returns False, else raises RuntimeError with a message naming the variable. Otherwise delegates to from_pyfile with the variable's value and the same silent flag, returning its result.

calls: [Config.from_pyfile](configuration-loading.md#u-c4736c8beba8)

<a id="u-4131a01c47fc"></a>
### `Config.from_file`

`def from_file( self, filename: str | os.PathLike[str], load: t.Callable[[t.IO[t.Any]]…` · [src/flask/config.py:L256-L302][f1]

Reads a data file with a caller-supplied loader and merges the resulting mapping into the config via from_mapping.

The filename is joined to root_path and opened in text mode, or binary mode when text=False. On OSError: if silent is true and errno is ENOENT or EISDIR it returns False (ENOTDIR is not in this list, unlike from_pyfile); otherwise strerror is prefixed with 'Unable to load configuration file' and the error is re-raised. Errors raised by the loader propagate. On success it returns the from_mapping result, always True, and only uppercase keys are stored.

calls: [Config.from_mapping](configuration-loading.md#u-2e2d482fcf30)

<a id="u-2e2d482fcf30"></a>
### `Config.from_mapping`

`def from_mapping( self, mapping: t.Mapping[str, t.Any] | None = None, **kwargs: t.Any…` · [src/flask/config.py:L304-L321][f1]

Updates the config from a mapping and keyword arguments, keeping only keys that are uppercase.

The mapping and kwargs are merged into a temporary dict (kwargs win on conflict). Keys where str.isupper() is false are dropped silently. Non-string keys would fail on isupper (AttributeError). Always returns True.

<a id="u-b07075178acd"></a>
### `Config.from_object`

`def from_object(self, obj: object | str) -> None:` · [src/flask/config.py:L218-L254][f1]

Copies the uppercase attributes of an object or imported module into the config.

If obj is a string it is resolved by import_string (import errors propagate). It then iterates dir(obj) and, for each name that is entirely uppercase (str.isupper), sets the config value from getattr, including inherited attributes. Lowercase names are ignored. Dicts do not work because their keys are not attributes. Class properties are read from the class, not an instance, so properties would be stored as property objects.

<a id="u-3ea8469172b0"></a>
### `Config.from_prefixed_env`

`def from_prefixed_env( self, prefix: str = "FLASK", *, loads: t.Callable[[str], t.Any…` · [src/flask/config.py:L126-L185][f1]

Copies environment variables starting with '<PREFIX>_' into the config, parsing values and supporting nested dict keys with '__'.

Variables are processed in sorted name order. The prefix and its underscore are removed. The value goes through loads (default json.loads); any Exception is ignored and the raw string is kept. A key without '__' is set directly. A key containing '__' is split; each intermediate part is created as an empty dict if missing and then traversed, and the last part is assigned. If an intermediate existing value is not a dict-like object, the subscripting or assignment raises (not caught). Keys keep their original case, with no uppercase filter. It always returns True, even if no variables matched.

**Uncertainties.**

- The graph shows loads(value) with several candidate targets; it is a parameter, so the actual callable depends on the caller.

<a id="u-c4736c8beba8"></a>
### `Config.from_pyfile`

`def from_pyfile( self, filename: str | os.PathLike[str], silent: bool = False ) -> bool:` · [src/flask/config.py:L187-L216][f1]

Executes a Python file as a module and loads its uppercase names into the config.

The filename is joined to root_path (an absolute filename wins). The file is read in binary, compiled and executed in the namespace of a fresh module object named 'config' whose __file__ is set. OSError handling: if silent is true and errno is ENOENT, EISDIR or ENOTDIR it returns False; otherwise strerror is rewritten to 'Unable to load configuration file (...)' and the error is re-raised. Syntax errors and exceptions in the config code propagate. On success it calls from_object on the module and returns True. Arbitrary code in the file runs with full privileges.

calls: [Config.from_object](configuration-loading.md#u-b07075178acd)

<a id="u-619af47ae8b6"></a>
### `Config.get_namespace`

`def get_namespace( self, namespace: str, lowercase: bool = True, trim_namespace: bool…` · [src/flask/config.py:L323-L364][f1]

Returns a new dict of the config entries whose keys start with a given namespace prefix.

The prefix test is a plain startswith, so the caller must include the trailing underscore. With trim_namespace true (default) the prefix is removed from the keys; with lowercase true (default) the resulting keys are lowercased. Both are applied per key. Non-string keys would raise. Different original keys that collapse to the same output key overwrite each other in iteration order.

<a id="u-84a58fa1dd23"></a>
### `ConfigAttribute.__init__`

`def __init__( self, name: str, get_converter: t.Callable[[t.Any], T] | None = None ) …` · [src/flask/config.py:L23-L27][f1]

Stores the config key name (as __name__) and an optional converter applied when the value is read.

<a id="u-2eb173edb0e9"></a>
### `ConfigAttribute.__set__`

`def __set__(self, obj: App, value: t.Any) -> None:` · [src/flask/config.py:L46-L47][f1]

Descriptor write: stores the value in obj.config under the attribute's name, without applying any converter.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/config.py
