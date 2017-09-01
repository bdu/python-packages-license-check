### Python Package License Checker

Lists all installed Python packages (in sys.path) and their
corresponding licenses.

To get a list of all installed packages, along with their homepage and license link (if available):

    ./check.py

To get the license for just a subset of installed packages:

    ./check.py --pkg first_package second_package ...

If you're interested in digging deeper through GitHub to find a link to their licenses, we can use BeautifulSoup to try to scrape it from their homepage link and take a few reasonable guesses. It won't find them all, but if you have a long list of packages, it will save you having to manually reasearch a chunk of them. To do this, add the --do-soup option.

    ./check.py --do-soup

Output is a tab-separated list of

    package_name   homepage   license_url   version   license_type

It's pretty simple!
