# Date Parsing

**Capability.** Owns parsing of textual dates into epoch seconds: token scanning into a struct when accumulator, weekday/month/timezone name tables, validation, timezone adjustment, overflow-safe time_t conversion, and the public curl_getdate/capped variants.

Use this child to understand how HTTP-style and other date strings become time_t values, including the supported-format contract and the disabled-build #else branch. Consumers include the HSTS expiry parser.

**Depended on by.**

- [HSTS Cache](r10-hsts-cache.md) · graph-confirmed · 1 edge(s) · HSTS entry creation parses expiry stamps using the capped date parser.

Parent: [curl Codebase](r10-curl-source.md)

## Units (29)

<a id="u-c19bb098429e"></a>
### `Curl_getdate_capped`

`int Curl_getdate_capped(const char *p, time_t *tp)` · [lib/parsedate.c:L716-L720][f1]

Curl_getdate_capped parses via parsedate into *tp and returns 0 on success; it returns non-zero only for PARSEDATE_FAIL.

Unlike curl_getdate, overflow/underflow codes (PARSEDATE_LATER/SOONER) leave the clamped extreme (e.g. TIME_T_MAX) in *tp and still return success (0).

<a id="u-690215c4b472"></a>
### `checkday`

`UNITTEST int checkday(const char *check, size_t len)` · [lib/parsedate.c:L212-L260][f1]

Maps a weekday name to 0 (Mon) through 6 (Sun), or -1 when no day matched.

Returns -1 immediately for len<3. It case-insensitively matches on the first three letters via a switch on check[1]: 'o' plus m..n gives Monday(0); 'u' with t..e gives Tuesday(1) and with s..n gives Sunday(6); 'e' w..d gives Wednesday(2); 'h' t..u Thursday(3); 'r' f..i Friday(4); 'a' s..t Saturday(5). When len>3 and a day matched, the remaining suffix must equal daysuffix[day] case-insensitively via curl_strnequal and exactly len-3 long, otherwise -1 is returned.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- Non-alphabetic bytes at check[0]/check[2] are only rejected by falling through the equality tests; behavior for len>=3 but strings shorter than 3 characters is guarded only by the len<3 check on the caller-supplied len.

<a id="u-c0cc62b3be05"></a>
### `checkmonth`

`UNITTEST int checkmonth(const char *check, size_t len)` · [lib/parsedate.c:L265-L322][f1]

Maps a three-letter month abbreviation to 0 (Jan) through 11 (Dec), returning -1 for anything else.

Any len other than 3 returns -1. A case-insensitive switch on check[2] branches per month: 'n' accepts ja->0 and ju->5; 'b' fe->1; 'r' ma->2 and ap->3; 'y' ma->4; 'l' ju->6; 'g' au->7; 'p' se->8; 't' oc->9; 'v' no->10; 'c' de->11. All mismatches fall through to the final return -1.

<a id="u-d03a7b873ff2"></a>
### `checktz`

`UNITTEST int checktz(const char *check, size_t len)` · [lib/parsedate.c:L337-L386][f1]

Resolves a time zone name to its offset in seconds from GMT, or -1 if not found or illegal.

Returns -1 for len>4, for check[0] < 'A', and via fall-through at the end. len==1 indexes the tzone[] single-letter table (offset in minutes times 60) but rejects first>'Z' and 'J' (not a time zone). len==2 accepts only names ending in 'T': 'NT' gives 11*60*60, 'UT' gives 0, otherwise -1. len==3 rejects first>'Y', packs the name with MKTZ and bsearches tzthree, returning offset*60 on a hit. len==4 rejects first>'W' and bsearches tzfoura the same way; a bsearch miss in either 3- or 4-letter case falls through to return -1.

**Uncertainties.**

- checktz reads check[0] without a length-0 guard beyond len>4 rejection, so an empty string would read past the terminator only if the caller passed len==0; caller-supplied len trust is unverified.

<a id="u-c72deab5b96e"></a>
### `curl_getdate`

`time_t curl_getdate(const char *p, const time_t *unused)` · [lib/parsedate.c:L692-L710][f1]

Public curl_getdate: returns the parsed date as time_t or -1 on failure.

A NULL pointer returns -1 without parsing; the second argument is a legacy parameter that is ignored. On PARSEDATE_OK the parsed value is returned, except that a successful parse yielding exactly (time_t)-1 is bumped to 0 (parsed++) so -1 never indicates success; every other result code returns -1.

<a id="u-956d7c26424a"></a>
### `datecheck`

`static bool datecheck(struct when *w)` · [lib/parsedate.c:L602-L615][f1]

Validates the accumulated when struct before epoch conversion.

A missing time (dsecs==-1) becomes 0, since date-only strings are legal. Returns TRUE (failure) if mday, mon, or year is still -1, if year <1583 (Gregorian calendar introduced 1582), or if mday >31; otherwise FALSE (acceptable).

<a id="u-184919788566"></a>
### `datenum`

`static int datenum(const char *indate, const char **datep, struct when *w)` · [lib/parsedate.c:L520-L600][f1]

Consumes one numeric token and fills the first matching when field.

First, if no time was seen yet it tries match_time; success consumes the time and finishes. Otherwise curlx_str_number parses an integer capped at 99999999; any parse error returns PARSEDATE_FAIL. With the digit count it decides: (a) exactly 4 digits, value <=1400, tzoff unset, and the preceding char is '+' or '-' (checked via indate/date[-1]) means an RFC822 numeric zone: tzoff = ((val/100*60)+(val%100))*60, negated for '+' because local-vs-GMT math is reversed; (b) exactly 8 digits with year/month/day unset means compact YYYYMMDD: year=val/10000, mon=((val%10000)/100)-1 with mon>11 returning PARSEDATE_FAIL, mday=val%100; (c) else if mday unset and 0<val<32, mday=val; (d) else if year unset, year=val, with two-digit years mapped: >70 -> +1900, else +2000. If nothing matched, PARSEDATE_FAIL. On success *datep advances past the token.

**Notes.**

- failure: A numeric zone like +1400 is only recognized when tzoff is still -1; a second numeric zone later in the string would instead be tried as mday or year.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-9579a72db654"></a>
### `datestring`

`static int datestring(const char **datep, struct when *w)` · [lib/parsedate.c:L488-L518][f1]

Consumes one alphabetic token (up to NAME_LEN=10 letters) and tries to classify it as weekday, month, then time zone, in that priority, each only if the corresponding when field is still -1.

If the token reaches NAME_LEN letters it is rejected outright. checkday, checkmonth and checktz decide recognition; the first that succeeds returns PARSEDATE_OK after advancing *datep past the token. If none matches, the string is bad and PARSEDATE_FAIL (-1) is returned without advancing. Note checktz returns 0 for GMT/Zulu, which counts as found because the code tests != -1.

**Notes.**

- condition: A token that already resembles a weekday is never tried as a month or timezone; classification order is wday, mon, tzoff, gated on each field being unset.

<a id="u-5df4e4537090"></a>
### `initwhen`

`static void initwhen(struct when *w)` · [lib/parsedate.c:L483-L486][f1]

Sets all six struct when fields to -1 (unknown).

<a id="u-4049b731cda0"></a>
### `match_time`

`static bool match_time(const char *date, struct when *w, char **endp)` · [lib/parsedate.c:L441-L467][f1]

Parses HH:MM or HH:MM:SS at 'date' into w->dsecs and reports the consumed extent.

Hours are parsed with oneortwodigit and must be <24, followed by ':' and a digit for minutes; minutes must be <60. If a second ':' plus digit follows, seconds are parsed and accepted only when <=60 (permitting a leap second of 60); without a seconds field HH:MM is accepted. On any mismatch returns FALSE leaving w untouched. On success stores (hh*3600 + mm*60 + ss) in w->dsecs, copies the end pointer into *endp and returns TRUE.

**Notes.**

- failure: A seconds value of 60 is accepted as valid, so dsecs can represent a leap second.

<a id="u-3ecc84b677da"></a>
### `mktimet`

`static int mktimet(curl_off_t seconds, time_t *output)` · [lib/parsedate.c:L630-L649][f1]

Squeezes a curl_off_t seconds value into a time_t, detecting overflow/underflow.

With SIZEOF_TIME_T < 5 (narrow signed time_t): seconds above TIME_T_MAX yields *output=TIME_T_MAX and PARSEDATE_LATER; below TIME_T_MIN yields *output=TIME_T_MIN and PARSEDATE_SOONER. Otherwise, if time_t is unsigned (HAVE_TIME_T_UNSIGNED), a negative value stores 0 and returns PARSEDATE_SOONER. In all remaining cases *output=(time_t)seconds and PARSEDATE_OK is returned.

**Notes.**

- failure: Overflow/underflow returns the clamped extreme value, not an error sentinel, so callers must check the return code.

<a id="u-d347720c4d89"></a>
### `oneortwodigit`

`static int oneortwodigit(const char *date, const char **endp)` · [lib/parsedate.c:L429-L438][f1]

Parses a one- or two-digit decimal number at 'date' (caller guarantees a leading digit).

If the next byte is also a digit it consumes two bytes and returns tens+ones; otherwise it consumes one byte and returns the single digit value. Sets *endp past the consumed digits.

<a id="u-dc81ce2ade4c"></a>
### `parsedate`

`static int parsedate(const char *date, time_t *output)` · [lib/parsedate.c:L651-L681][f1]

Parses a date string into a time_t by scanning up to 6 whitespace/separator-delimited parts.

It initializes a when struct, then loops: skip() moves past non-alphanumerics; an alphabetic byte goes to datestring, a digit to datenum (which receives the original pointer for +/- lookahead). Either returning nonzero aborts with that code immediately. After the loop, datecheck rejects incomplete or pre-Gregorian dates with PARSEDATE_FAIL; otherwise seconds come from time2epoch, are shifted by tzadjust, and are narrowed via mktimet whose return code (OK, LATER, SOONER, or FAIL propagation) is returned. When CURL_DISABLE_PARSEDATE is defined the stub writes 0 to *output and returns PARSEDATE_OK regardless of input.

**Notes.**

- condition: More than 6 parts stops scanning early; remaining text is ignored rather than causing failure.

<a id="u-aff261ffec3d"></a>
### `skip`

`static void skip(const char **date)` · [lib/parsedate.c:L388-L393][f1]

Advances the date pointer past every byte that is not alphanumeric, stopping at the NUL terminator.

<a id="u-3663832880fd"></a>
### `time2epoch`

`static curl_off_t time2epoch(struct when *w)` · [lib/parsedate.c:L413-L424][f1]

Converts a filled struct when into seconds since the Unix epoch in GMT, without timezone adjustment.

It counts days from 1970 as (year-1970)*365 plus leap days: leap days computed from (y/4 - y/100 + y/400) - LEAP_DAYS_BEFORE_1969 where y is the year decremented for Jan/Feb so leap-day counting is correct before March; plus a cumulative-days table (non-leap baseline, 59 for March index means February never gets an extra day here) and mday-1. Returns days*86400 + dsecs as curl_off_t.

**Uncertainties.**

- The cumulative_days table has no leap-year adjustment for the current year, so the treatment of Feb 29 for leap years relies on the leap_days term and is not independently verifiable from this function alone.

<a id="u-b45324b333db"></a>
### `tzadjust`

`static void tzadjust(curl_off_t *tp, struct when *w)` · [lib/parsedate.c:L617-L628][f1]

Applies the parsed timezone offset to the epoch seconds.

An unknown tzoff (-1) is treated as 0. If tzoff>0 and adding it would exceed CURL_OFF_T_MAX, *tp is clamped to CURL_OFF_T_MAX; otherwise *tp += tzoff. No underflow clamp is done because the code requires year > 1582.

<a id="u-4defc8516b47"></a>
### `tzcompare`

`static int tzcompare(const void *m1, const void *m2)` · [lib/parsedate.c:L324-L329][f1]

bsearch comparator for struct tzinfo entries; subtracts the two packed tz keys and returns the difference as the ordering.

<a id="u-afe5e4955092"></a>
### `parsedate.c module code (L1–L105)`

`struct tzinfo` · [lib/parsedate.c:L106-L109][f1]

File header, license, supported date-format summary, includes, and exported weekday/month name tables (Curl_wkday, Curl_month) guarded by !CURL_DISABLE_PARSEDATE || !CURL_DISABLE_FTP || !CURL_DISABLE_FILE || USE_GNUTLS; plus PARSEDATE_* result defines, struct tzinfo, the single/three/four-letter timezone offset tables with MKTZ packing, DST and LOWERCASE macros.

**Notes.**

- side_effect: Curl_wkday/Curl_month are exported for FTP and FILE code, not only for this parser.

<a id="u-4fd1098110b1"></a>
### `parsedate.c module code (L329–L336)`

`module_region` · [lib/parsedate.c:L329-L336][f1]

@unittest comment preceding checktz; no code.

<a id="u-c7fedb750273"></a>
### `parsedate.c module code (L393–L395)`

`module_region` · [lib/parsedate.c:L393-L395][f1]

Comment only between skip and struct when; no code.

<a id="u-c7b1aa328b48"></a>
### `parsedate.c module code (L403–L412)`

`module_region` · [lib/parsedate.c:L403-L412][f1]

Leap-day constant LEAP_DAYS_BEFORE_1969 (477) and SECONDS_PER_DAY (86400) defines plus the time2epoch doc comment; non-behavioral.

<a id="u-ca4702d2424b"></a>
### `parsedate.c module code (L424–L428)`

`module_region` · [lib/parsedate.c:L424-L428][f1]

Comment only between time2epoch and oneortwodigit; no code.

<a id="u-afdc05ccfc44"></a>
### `parsedate.c module code (L438–L440)`

`module_region` · [lib/parsedate.c:L438-L440][f1]

Comment only before match_time; no code.

<a id="u-8a81e39af694"></a>
### `parsedate.c module code (L467–L482)`

`module_region` · [lib/parsedate.c:L467-L482][f1]

parsedate() result-code contract comment, NAME_LEN define, and the #else disabled-parsedate branch context; mostly non-behavioral glue around initwhen/datestring.

<a id="u-7c41f4f685df"></a>
### `parsedate.c module code (L681–L683)`

`module_region` · [lib/parsedate.c:L681-L683][f1]

End of the primary parsedate definition; no code.

<a id="u-81eed0460700"></a>
### `parsedate.c module code (L689–L691)`

`module_region` · [lib/parsedate.c:L689-L691][f1]

#endif closing the disabled-parsedate conditional; no code.

<a id="u-892089b769cb"></a>
### `parsedate.c module code (L710–L715)`

`module_region` · [lib/parsedate.c:L710-L715][f1]

Comment block above Curl_getdate_capped describing its capped behavior; no code.

<a id="u-0b1b8f44bb58"></a>
### `parsedate.c module code (L109–L211)`

`module_region` · [lib/parsedate.c:L109-L211][f1]

Between checkday and checkmonth there is only the @unittest 4781 comment; no code.

<a id="u-a86d8071fb5d"></a>
### `when`

`struct when` · [lib/parsedate.c:L396-L403][f1]

Defines struct when, the parser's accumulator: wday (0-6 Mon-Sun), mon (0-11), mday (1-31), dsecs (seconds into the day), year (>=1583), and tzoff (seconds).

Every field is -1 when unknown, per the comment.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/parsedate.c
