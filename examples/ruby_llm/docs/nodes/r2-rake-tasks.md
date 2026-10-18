# Rake Tasks

**Capability.** Maintenance tasks: gem release steps, model-registry database loading, and VCR cassette re-recording workflows.

Use for release automation, populating the ActiveRecord model registry from models.json, and re-recording provider cassettes (full or per-provider).

**Depends on.**

- [acts\_as Declarations](r2-acts-as-declarations.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](r2-ruby-llm.md)

## Units (9)

<a id="u-8a9da7de6813"></a>
### `release.rake module code (L1–L67)`

`module_region` · [lib/tasks/release.rake:L1-L67][f1]

Defines three release rake tasks.

release:prepare invokes release:refresh_stale_cassettes, runs 'overcommit --run' via sh, then invokes the `models` task. release:refresh_stale_cassettes treats every yml under spec/fixtures/vcr_cassettes older than 1 day (mtime difference divided by 86400) as stale, deletes it, and if any were removed re-records everything with 'bundle exec rspec' via system, exiting with status 1 when the suite fails; otherwise it reports no stale cassettes. release:verify_cassettes performs the same staleness scan non-destructively, listing stale files and exiting 1 if any exist, else confirming freshness.

**Notes.**

- side_effect: refresh_stale_cassettes permanently deletes stale cassette files before re-recording.
- failure: verify_cassettes exits with code 1 when any cassette exceeds the 1-day threshold; refresh exits 1 when 'bundle exec rspec' fails.

**Uncertainties.**

- sh 'overcommit --run' raises on non-zero exit (standard sh behavior); the rake dependency on Rake::Task['release:refresh_stale_cassettes'] and 'models' resolves at invoke time and is not verifiable here.
- verify_cassettes builds stale_files paths but never uses them beyond collection; whether that is intentional dead code is not stated.

<a id="u-0fffeb0c8dbb"></a>
### `ruby_llm.rake module code (L1–L15)`

`module_region` · [lib/tasks/ruby_llm.rake:L1-L15][f2]

Defines ruby_llm:load_models (dependent on :environment): when RubyLLM.config.model_registry_class is set, it loads the registry from models.json via RubyLLM.models.load_from_json!, constantizes the registry class, calls save_to_database on it, and prints the loaded count; when the registry class is not configured it only prints guidance to run the install generator.

**Notes.**

- failure: Missing registry configuration is handled by printing an instruction message rather than raising; constantize on a bad name would still raise NameError.

**Uncertainties.**

- Behavior of load_from_json! and save_to_database is defined in RubyLLM, outside this file.

<a id="u-4f85bfeef3bd"></a>
### `vcr.rake module code (L1–L4)`

`module_region` · [lib/tasks/vcr.rake:L1-L4][f3]

File header requiring 'dotenv/load'; contains no behavior of its own.

<a id="u-984cd01d6966"></a>
### `record_all_cassettes`

`def record_all_cassettes(cassette_dir)` · [lib/tasks/vcr.rake:L5-L12][f3]

Re-records cassettes for every provider by removing the whole cassette directory with FileUtils.rm_rf, recreating it with mkdir_p, running the test suite via run_tests, and printing a review reminder.

calls: [run_tests](r2-rake-tasks.md#u-d706b33dacce)

<a id="u-20cff4ee712b"></a>
### `record_for_providers`

`def record_for_providers(providers, cassette_dir)` · [lib/tasks/vcr.rake:L14-L44][f3]

Re-records cassettes for a chosen provider subset.

With an empty provider list, or after finding providers not present in RubyLLM::Provider.providers, it prints usage or the invalid names plus the available list and returns without recording. Otherwise it computes matching cassettes via find_matching_cassettes, printing 'No cassettes found' or deleting them via delete_cassettes, then always runs the test suite via run_tests and reminds the user to review cassettes for sensitive information.

calls: [find_matching_cassettes](r2-rake-tasks.md#u-343a4e83e281), [delete_cassettes](r2-rake-tasks.md#u-cf9c35016d96), [run_tests](r2-rake-tasks.md#u-d706b33dacce)

<a id="u-343a4e83e281"></a>
### `find_matching_cassettes`

`def find_matching_cassettes(dir, providers)` · [lib/tasks/vcr.rake:L46-L62][f3]

Finds cassette yml files under dir whose basename matches a provider name: either '^[^_]*_<provider>_' (provider in the first section, as in chat_openai_) or '_<provider>_[^_]+' (provider mid-name, as in _openai_gpt4_).

A file matching any requested provider is added once (inner break); returns the collected file paths.

**Uncertainties.**

- The regexes only inspect the filename, so provider names that are substrings of other tokens between underscores could over-match; not provable from this file.

<a id="u-cf9c35016d96"></a>
### `delete_cassettes`

`def delete_cassettes(cassettes)` · [lib/tasks/vcr.rake:L64-L70][f3]

Prints how many cassettes will be deleted, then deletes each file with File.delete after printing its basename.

No existence check precedes deletion.

**Uncertainties.**

- If a listed file no longer exists, File.delete raises Errno::ENOENT; whether callers pre-filter existence is not shown here.

<a id="u-d706b33dacce"></a>
### `run_tests`

`def run_tests` · [lib/tasks/vcr.rake:L72-L74][f3]

Runs the full suite with system('bundle exec rspec') and aborts the process with 'Tests failed' when the command returns a falsy (non-zero) exit status.

<a id="u-d6775079b96e"></a>
### `vcr.rake module code (L74–L92)`

`module_region` · [lib/tasks/vcr.rake:L74-L92][f3]

Defines the vcr:record rake task taking a comma-separated :providers argument.

It requires fileutils and ruby_llm lazily, ensures the cassette directory spec/fixtures/vcr_cassettes exists, and builds the provider list from args.extras plus args[:providers], downcasing and dropping nils. When the list includes 'all' it delegates to record_all_cassettes; otherwise to record_for_providers.

calls: [record_all_cassettes](r2-rake-tasks.md#u-984cd01d6966), [record_for_providers](r2-rake-tasks.md#u-20cff4ee712b)

**Uncertainties.**

- Whether an omitted :providers argument (nil, no extras) reaches record_for_providers with an empty list and prints usage, or behaves otherwise, depends on Rake's arg handling not shown here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/release.rake
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/ruby_llm.rake
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/vcr.rake