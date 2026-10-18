# Filename pattern matching

**Capability.** A self-contained wildcard matcher used for e.g. --wildcard file lists, with a platform fnmatch backend and a bundled fallback parser.

Read Curl_fnmatch for the entry point; the fallback recursively parses bracket sets and matches with backtracking. It depends on nothing outside this file.

Parent: [Shared infrastructure utilities](r7-shared-infra.md)

## Units (9)

<a id="u-3452178878d0"></a>
### `curl_fnmatch-c-preprocessor-blocks`

`enum` · [lib/curl_fnmatch.c:L48-L52][f1]

Preprocessor region of the fallback fnmatch implementation.

It defines charset sizing constants (CURLFNM_CHARSET_LEN of 256, CURLFNM_CHSET_SIZE adding 15 slots), indexes CURLFNM_NEGATE and the ten class slots (ALNUM, DIGIT, XDIGIT, ALPHA, PRINT, BLANK, LOWER, GRAPH, SPACE, UPPER), the setcharset_state and parsekey_state parser state enums, the char_class enum, and the SETCHARSET_OK/FAIL result codes. All are compile-time declarations consumed by the functions in this file; they carry no runtime behavior of their own.

<a id="u-c79c8a900ed1"></a>
### `Curl_fnmatch`

`int Curl_fnmatch(void *ptr, const char *pattern, const char *string)` · [lib/curl_fnmatch.c:L398-L415][f1]

Platform-backed implementation used when HAVE_FNMATCH is defined.

It ignores ptr, returns CURL_FNMATCH_FAIL for NULL pattern or string, and maps fnmatch(pattern, string, 0): 0 to CURL_FNMATCH_MATCH, FNM_NOMATCH to CURL_FNMATCH_NOMATCH, and any other result to CURL_FNMATCH_FAIL.

uses: [curl_fnmatch.h module code (L1–L45)][f2]

**Uncertainties.**

- Exact fnmatch() behavior (flags disabled here) is platform-defined

<a id="u-bc0ba22cd837"></a>
### `lib/curl_fnmatch.c:Curl_fnmatch`

`int Curl_fnmatch(void *ptr, const char *pattern, const char *string)` · [lib/curl_fnmatch.c:L382-L391][f1]

Internal fallback implementation of the pattern matcher used when the platform lacks fnmatch().

It ignores the ptr argument, returns CURL_FNMATCH_FAIL when pattern or string is NULL, and otherwise delegates to loop(), returning its MATCH/NOMATCH verdict directly.

calls: [loop](r7-fnmatch-pattern.md#u-f5e85d9250df)

**Uncertainties.**

- Which of the two Curl_fnmatch definitions is compiled depends on HAVE_FNMATCH; only one exists per build

<a id="u-48f1e3b7c279"></a>
### `charclass`

`static char_class charclass(unsigned char c)` · [lib/curl_fnmatch.c:L125-L134][f1]

Classifies one byte as CCLASS_UPPER, CCLASS_LOWER, CCLASS_DIGIT, or CCLASS_OTHER, checking upper, lower, then digit in that order.

Used to keep range endpoints within the same class so that ranges in non-contiguous encodings still expand sensibly.

<a id="u-f5e85d9250df"></a>
### `loop`

`static int loop(const unsigned char *pattern, const unsigned char *string)` · [lib/curl_fnmatch.c:L315-L377][f1]

Greedy wildcard matcher with backtracking to the most recent '*', returning CURL_FNMATCH_MATCH or CURL_FNMATCH_NOMATCH.

It allows at most two '*' tokens per pattern; a third returns NOMATCH. In the main loop, on '*' it skips consecutive '*' (each '?' after the star consumes one string character or fails on end of string), returns MATCH immediately if the pattern ends, and otherwise records the star position. For a normal token it applies matchtoken; a -1 (set syntax error) is NOMATCH, a match advances both cursors, and a mismatch backtracks to the last star with the star's string cursor advanced by one — no star recorded means NOMATCH. When the pattern is exhausted but string remains, it backtracks to a star if any, else NOMATCH. After the string ends, a trailing run of '*' is collapsed (a '?' among them yields NOMATCH); the result is MATCH only when the pattern is also exhausted.

**Notes.**

- condition: maxstars is 2, so only two '*' tokens are permitted in a whole pattern; more return NOMATCH.
- contract: Backtracking is to the most recent star only, not all stars; combined with the two-star limit this bounds the search.

calls: [matchtoken](r7-fnmatch-pattern.md#u-12e49ea7e4bb)

**Uncertainties.**

- UTF/Unicode: header claims '*' works with UTF strings but '?' matches bytes; per-byte semantics of multibyte sequences are not established from this source

<a id="u-12e49ea7e4bb"></a>
### `matchtoken`

`static int matchtoken(const unsigned char **pp, const unsigned char **sp)` · [lib/curl_fnmatch.c:L252-L312][f1]

Matches one pattern token against one string character, advancing both caller pointers and returning 1 on match, 0 on mismatch, or -1 when the pattern set has a syntax error.

'?' consumes any single character without inspection. '\' matches the next pattern byte (an escaped literal) exactly against *s; if the byte after the backslash is null, the backslash itself is matched literally. '[' parses the set from a copy of the pointer (so the original is untouched on syntax error) and tests *s against explicit membership first, then against class flags in the fixed order alnum, alpha, digit, xdigit, print, space, upper, lower, blank, graph; CURLFNM_NEGATE inverts the result. On match both pointers advance past the set (including the closing ']'); on -1 the caller's pointers are unchanged. The default case is an exact literal comparison.

**Notes.**

- contract: Return -1 signals set-syntax failure, which the caller maps to NOMATCH.

calls: [setcharset](r7-fnmatch-pattern.md#u-e2782737e523)

**Uncertainties.**

- Only the first matching class flag in the fixed order takes effect; overlapping flags (e.g. space and blank both ISBLANK) are behaviorally redundant per this code

<a id="u-2d0707c1c32a"></a>
### `parsekeyword`

`static int parsekeyword(const unsigned char **pattern, unsigned char *charset)` · [lib/curl_fnmatch.c:L69-L122][f1]

Parses a '[:keyword:]' class keyword inside a bracket expression and flags the matching class in the charset.

It scans lowercase letters until ':', then expects a closing ']'; a keyword longer than 9 characters, a non-lowercase leading character, or a character other than ']' after the second ':' returns SETCHARSET_FAIL without advancing the caller's pointer. On success it advances the caller's pattern pointer past the keyword, then compares the keyword against the ten supported names (digit, alnum, alpha, xdigit, print, graph, space, blank, upper, lower), setting the corresponding CURLFNM_* slot in charset to 1; an unknown keyword fails.

uses: [setcharset](r7-fnmatch-pattern.md#u-e2782737e523)

**Uncertainties.**

- ISLOWER's exact definition is not in this file

<a id="u-29d875a83296"></a>
### `setcharorrange`

`static void setcharorrange(const unsigned char **pp, unsigned char *charset)` · [lib/curl_fnmatch.c:L137-L156][f1]

Records one character in the charset, or a character range when the next pattern bytes form 'c-end' with both endpoints in the same class and end >= c.

It always sets charset[c]=1 first. A range is only expanded when c is alphanumeric, the next byte is '-', and after treating a trailing backslash as an escaped endpoint, endrange is >= c and charclass(endrange) equals charclass(c); then every byte from c to endrange whose class matches is also set, since class members may not be contiguous. If any condition fails, only the single character is recorded and the '-' and following bytes remain for later pattern scanning. The caller's pattern pointer is advanced only on a successful range.

calls: [charclass](r7-fnmatch-pattern.md#u-48f1e3b7c279)

**Uncertainties.**

- An incomplete range like 'a-' at buffer end consumes only 'a' per this reading; behavior of subsequent bytes depends on setcharset

<a id="u-e2782737e523"></a>
### `setcharset`

`static int setcharset(const unsigned char **p, unsigned char *charset)` · [lib/curl_fnmatch.c:L159-L249][f1]

Parses a bracket set '[...]' from the pattern into a 256-entry charset plus class flags, returning SETCHARSET_OK (1) on success or SETCHARSET_FAIL (0) on syntax error or premature end of pattern.

It clears the charset first. In the DEFAULT state: ']' returns OK if something was already found, otherwise it is treated as a literal member and the state moves to RIGHTBR; '[' tries a '[:keyword:]' via parsekeyword and otherwise records '[' literally; '^' or '!' sets CURLFNM_NEGATE only as the first element (a second negation character becomes a literal); '\' escapes the following byte and records it, with a trailing backslash at end of pattern recording '\' literally; any other byte is handled by setcharorrange. In RIGHTBR, '[' moves to RIGHTBRLEFTBR, ']' returns OK, a printable character becomes a literal member returning to DEFAULT, and any other byte fails. In RIGHTBRLEFTBR, ']' returns OK and any other byte is recorded, returning to DEFAULT. A null pattern byte at any loop iteration fails.

**Notes.**

- failure: The comment documents a goto fail used instead of a direct return to avoid a Solaris compiler warning; it returns SETCHARSET_FAIL.

calls: [parsekeyword](r7-fnmatch-pattern.md#u-2d0707c1c32a), [setcharorrange](r7-fnmatch-pattern.md#u-29d875a83296)

**Uncertainties.**

- Whether ISPRINT-based RIGHTBR entry rejects control bytes exactly as non-printable depends on ISPRINT's definition

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_fnmatch.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_fnmatch.h
