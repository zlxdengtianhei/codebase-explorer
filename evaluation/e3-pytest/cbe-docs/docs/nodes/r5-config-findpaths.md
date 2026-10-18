# Rootdir and config-file discovery

**Capability.** determine_setup and its helpers in src/_pytest/config/findpaths.py: converting free args to directories, walking ancestors for pytest.ini/.pytest.ini/pyproject.toml/tox.ini/setup.cfg, parsing ini config (re-raising iniconfig.ParseError as UsageError), computing common ancestors and filesystem roots.

Use this to trace how pytest pins down rootdir, inipath and inicfg. locate_config and load_config_dict_from_file are the workhorses called by determine_setup.

**Depends on.**

- [Config exceptions and private-API guards](r5-config-api-guards.md) · model-inferred · 0 edge(s)

Parent: [Configuration bootstrapping](r5-config-bootstrapping.md)

## Units (9)

<a id="u-4c6e4cc79376"></a>
### `determine_setup`

`def determine_setup( *, inifile: str | None, args: Sequence[str], rootdir_cmd_arg: st…` · [src/_pytest/config/findpaths.py:L180-L231][f1]

Determines rootdir, inifile and ini config from command-line data, returning (rootdir, inipath, inicfg).

With --inifile given, the file is absolutized and loaded (empty dict if it yields nothing) and, absent --rootdir, rootdir becomes the inifile's parent. Otherwise the common ancestor of the arg directories is computed and locate_config searched there; if nothing is found and no --rootdir was given, rootdir falls back to the nearest ancestor (or its parents) containing setup.py; failing that, locate_config is retried over the arg dirs, and finally rootdir becomes the common ancestor of invocation_dir and the args' ancestor, unless that is the filesystem root, in which case the args' ancestor is kept. An explicit --rootdir is expandvars'd, absolutized, and must be an existing directory or UsageError is raised; it overrides any computed rootdir. The final rootdir is asserted non-None.

calls: [findpaths-get_dirs_from_args](r5-config-findpaths.md#u-7732fc94d153), [locate_config](r5-config-findpaths.md#u-a3ddc4c32f5b), [get_common_ancestor](r5-config-findpaths.md#u-058cea11be2b)

**Uncertainties.**

- Behavior when dirs is empty (all args are options) relies on get_common_ancestor falling back to invocation_dir; the is_fs_root guard then keeps ancestor, which may equal invocation_dir.

<a id="u-a3ddc4c32f5b"></a>
### `locate_config`

`def locate_config( invocation_dir: Path, args: Iterable[Path], ) -> tuple[Path | None…` · [src/_pytest/config/findpaths.py:L96-L126][f1]

Searches argument paths (and their ancestor directories) for the first valid pytest config file among pytest.ini, .pytest.ini, pyproject.toml, tox.ini, setup.cfg.

Arguments starting with '-' are dropped; if none remain, the invocation directory is used. For each argument, each base in (argpath plus parents) is tested: the first candidate that load_config_dict_from_file accepts returns (base, file, config). pyproject.toml is remembered as a fallback: if no file yields a config dict, the first-seen pyproject.toml is returned with its parent as rootdir and an empty dict, otherwise (None, None, {}).

calls: [findpaths-load_config_dict_from_file](r5-config-findpaths.md#u-d0f6b558f6a5)

**Uncertainties.**

- Search order across multiple args is arg-by-arg; the first config found for the earliest arg wins, even if a later arg has a nearer config.

<a id="u-d0f6b558f6a5"></a>
### `findpaths-load_config_dict_from_file`

`def load_config_dict_from_file( filepath: Path, ) -> ConfigDict | None:` · [src/_pytest/config/findpaths.py:L41-L88][f1]

Loads pytest configuration from a file by suffix, returning a config dict or None when the file holds no valid pytest configuration.

For '.ini' files it parses via _parse_ini_config and returns the [pytest] section's items; a 'pytest.ini' file returns {} even when empty (it is always authoritative). For '.cfg' files it returns the [tool:pytest] items if present, but a plain '[pytest]' section triggers fail(CFG_PYTEST_SECTION...) about the unsupported setup.cfg section. For '.toml' files it reads UTF-8 text and parses with tomllib (stdlib on 3.11+, tomli otherwise); a TOMLDecodeError becomes UsageError with the file path and message. If tool.pytest.ini_options exists, all scalar values are converted to str (lists kept as-is) for compatibility with the string-oriented config system. Any other suffix, or a recognized file without the required section, yields None.

calls: [_parse_ini_config](r5-config-findpaths.md#u-5f6c01f43520); raises: [UsageError](r5-config-api-guards.md#u-4e183a5c29b3)

**Uncertainties.**

- raise/_outcomes.fail's exact control flow is defined in _pytest.outcomes, not here.

<a id="u-5f6c01f43520"></a>
### `_parse_ini_config`

`def _parse_ini_config(path: Path) -> iniconfig.IniConfig:` · [src/_pytest/config/findpaths.py:L29-L38][f1]

Parses an ini-style file with iniconfig.IniConfig; an iniconfig.ParseError is re-raised as UsageError carrying the original message, chained from the parse error.

<a id="u-7732fc94d153"></a>
### `findpaths-get_dirs_from_args`

`def get_dirs_from_args(args: Iterable[str]) -> list[Path]:` · [src/_pytest/config/findpaths.py:L155-L156][f1]

Converts free command-line arguments to existing directories for rootdir computation.

Arguments starting with '-' are treated as options and skipped; node ids are cut at '::' to keep only the file part; each remaining argument is made absolute and, if it exists, mapped to itself when a directory or to its parent when a file. Non-existent paths are dropped by safe_exists.

<a id="u-058cea11be2b"></a>
### `get_common_ancestor`

`def get_common_ancestor( invocation_dir: Path, paths: Iterable[Path], ) -> Path:` · [src/_pytest/config/findpaths.py:L129-L152][f1]

Computes the common ancestor directory of the given paths.

Non-existent paths are skipped. The first existing path seeds the ancestor; subsequent paths either leave it (if it contains them or equals it), replace it (if it is inside it), or shrink it to commonpath(path, ancestor) when that is not None. If no path exists the invocation_dir is used; a file ancestor is replaced by its parent directory.

uses: [findpaths-get_dirs_from_args](r5-config-findpaths.md#u-7732fc94d153)

**Uncertainties.**

- If commonpath returns None the non-shared path is silently ignored, leaving the previous ancestor.

<a id="u-c2bcb1bd443c"></a>
### `is_fs_root`

`def is_fs_root(p: Path) -> bool:` · [src/_pytest/config/findpaths.py:L234-L239][f1]

Returns True when the path is a filesystem root: os.path.splitdrive leaves exactly os.sep after the drive ('/' on Unix, 'C:\' on Windows).

<a id="u-22fcfe0fa5ed"></a>
### `findpaths.py module code (L1–L28)`

`module_region` · [src/_pytest/config/findpaths.py:L1-L28][f1]

Preamble importing os/pathlib/sys, iniconfig, tomli/tomllib, UsageError, fail and pathlib helpers, plus a TYPE_CHECKING-only ConfigDict alias (dict[str, str | list[str]]) used as the return type of the config loaders.

<a id="u-1f6f867ab1fe"></a>
### `findpaths.py module code (L174–L179)`

`module_region` · [src/_pytest/config/findpaths.py:L174-L179][f1]

Defines the module constant CFG_PYTEST_SECTION, the message text used when a legacy '[pytest]' section is found in a setup.cfg file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/findpaths.py
