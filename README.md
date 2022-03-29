# phylum-ci

Python package for handling CI and other integrations

## Local Development

Here's how to set up `phylum-ci` for local development.

1. Clone the `phylum-ci` repo locally

    ```sh
    git clone git@github.com:phylum-dev/phylum-ci.git
    ```

2. Ensure [poetry](https://python-poetry.org/docs/) is installed
3. Install dependencies with `poetry`, which will automatically create a virtual environment:

    ```sh
    cd phylum-ci
    poetry install
    ```

4. Create a branch for local development:

    ```sh
    git checkout -b <name-of-your-branch>
    ```

    Now you can make your changes locally.

5. When you're done making changes, check that your changes pass the tests:

    ```sh
    poetry run pytest
    ```

6. Commit your changes and push your branch to GitHub:

    ```sh
    git add .
    git commit -m "Description of the changes goes here"
    git push --set-upstream origin <name-of-your-branch>
    ```

7. Submit a pull request through the GitHub website
