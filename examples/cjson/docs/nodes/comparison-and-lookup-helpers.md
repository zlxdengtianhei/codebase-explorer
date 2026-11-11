# Comparison and lookup helpers

**Capability.** Provides equality tests, case-insensitive string comparison, locale-aware decimal handling, and key-based object lookup.

This module centralizes the predicates used by higher-level features: deep equality, relative-epsilon double comparison, and object member lookup with case sensitivity control. Number rendering and locale decimal-point translation also live here.

**Depends on.**

- [JSON printing and serialization](json-printing-and-serialization.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Duplication and replacement](duplication-and-replacement.md) · graph-confirmed · 1 edge(s)
- [JSON Patch application](json-patch-application.md) · graph-only · 2 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 2 edge(s)
- [JSON parser](json-parser.md) · graph-only · 1 edge(s)
- [JSON printing and serialization](json-printing-and-serialization.md) · graph-only · 1 edge(s)

Parent: [Item Utility Toolkit](item-utility-toolkit.md)

## Units (6)

<a id="u-ebaf707174c1"></a>
### `cJSON_Compare`

`CJSON_PUBLIC(cJSON_bool) cJSON_Compare(const cJSON * const a, const cJSON * const b, …` · [cJSON.c:L3072-L3195][f1]

Deep structural equality test.

Returns false for NULL arguments, differing low type bytes, or an invalid type. Identical pointers are equal. False/True/NULL need only matching types; numbers compare with the epsilon-based compare_double; String and Raw compare valuestrings with strcmp (NULL valuestring is unequal); arrays compare element-wise recursively and require equal lengths; objects require, in both directions, that every key of one exist in the other with a recursively equal value (an O(n^2) pairwise scan, as noted in the source).

<a id="u-dc674c51daff"></a>
### `case_insensitive_strcmp`

`static int case_insensitive_strcmp(const unsigned char *string1, const unsigned char …` · [cJSON.c:L133-L154][f1]

Case-insensitive string comparison that treats any NULL argument as unequal (returns 1) and identical pointers as equal (0); otherwise compares with tolower until a mismatch or NUL, returning the tolower difference.

<a id="u-438dd0368a51"></a>
### `compare_double`

`static cJSON_bool compare_double(double a, double b)` · [cJSON.c:L589-L593][f1]

Relative-epsilon double comparison: |a-b| <= max(|a|,|b|)*DBL_EPSILON, so equality is scale-dependent rather than exact.

<a id="u-ef3398f57b63"></a>
### `get_decimal_point`

`static unsigned char get_decimal_point(void)` · [cJSON.c:L279-L287][f1]

Returns the locale's decimal point character when ENABLE_LOCALES is defined (via localeconv), otherwise '.'; used to translate between JSON '.' and strtod/sprintf expectations.

<a id="u-23f8c0af73d3"></a>
### `print_number`

`static cJSON_bool print_number(const cJSON * const item, printbuffer * const output_b…` · [cJSON.c:L596-L663][f1]

Renders an item's number into the output buffer.

NaN and infinity print as "null"; a double equal to the stored integer prints with %d; otherwise it tries %1.15g and re-parses with sscanf to verify round-trip via compare_double, falling back to %1.17g if recovery fails. If sprintf returns negative or exceeds the 25-char scratch buffer it returns false. It then ensures length+1 bytes, copies the digits translating the locale decimal point back to '.', NUL-terminates, and advances the offset; ensure failure returns false.

<a id="u-4a3b5395c9a4"></a>
### `cJSON.c-object-item-access`

`static cJSON *get_object_item(const cJSON * const object, const char * const name, co…` · [cJSON.c:L1951-L1981][f1]

get_object_item scans an object's children for a matching key, using strcmp when case_sensitive and case_insensitive_strcmp otherwise, and returns NULL when the object or name is NULL, no match is found, or the found element's string is NULL.

cJSON_GetObjectItem and cJSON_GetObjectItemCaseSensitive are the insensitive/sensitive public wrappers; cJSON_HasObjectItem reports whether the insensitive lookup finds the key.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
