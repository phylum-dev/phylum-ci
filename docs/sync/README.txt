This directory and any sub-directories is used to populate the "Integrations"
section of the Phylum documentation - https://docs.phylum.io/docs

Readme.com is currently used to host this documentation and the `rdme` CLI is
used to perform the synchronization. In order for that process to work, the
following requirements must be met:

* Docs to be included should be in markdown format
* All markdown files must
  * include front matter containing `category: 62cdf6722c2c1602a4b69643`
  * be named uniquely (name forms the URL 'slug')

The following are recommendations that should be met:

* Include a descriptive title as part of the front matter
  * Example: `title: GitLab CI Integration`
* Follow the existing naming patterns, when possible
* Keep the file names short so the resulting URL slugs will also be short

The first time a file is uploaded to the docs site, it may show up in the
wrong order within the section. A Phylum administrator with Readme.com
access can assist with re-ordering the page. This should only be required
the first time.
