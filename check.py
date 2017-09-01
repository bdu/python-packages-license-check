#!/usr/bin/env python
import pkg_resources
import argparse
import sys
import json
import requests

from pip.utils import get_installed_distributions
from collections import namedtuple

from bs4 import BeautifulSoup

class InstalledDistribution(object):
    meta_files_to_check = ['PKG-INFO', 'METADATA']

    def __init__(self, pip_obj, do_soup=False):
        for required_value in ['project_name', 'version', 'license_str', 'home_page', 'license_url']:
            if hasattr(pip_obj, required_value):
                setattr(self, required_value, getattr(pip_obj, required_value))
            else:
                setattr(self, required_value, "")
        self.pip_obj = pip_obj
        self.do_soup = do_soup
        self.found_license = False
        self._populate()

    def __repr__(self):
        return "{project_name}\t{home_page}\t{license_url}\t{version}\t{license_str}".format(**self.__dict__)

    def _populate(self):
        for metafile in self.meta_files_to_check:
            if not self.pip_obj.has_metadata(metafile):
                continue
            for line in self.pip_obj.get_metadata_lines(metafile):
                if 'License: ' in line:
                    self.license_str = line.split(': ', 1)[1]
                    self.found_license = True
                if 'Home-page: ' in line:
                    self.home_page = line.split(': ', 1)[1]
                    self._fetch_license_url()
        if not self.found_license:
            self.license_str = "unknown - no metafile found"

    def _fetch_license_url(self):
        github_proj = GithubProject.parse_url(self.home_page, self.do_soup)
        if github_proj:
            self.license_url = github_proj.license_url()
        else:
            self.license_url = "unknown - couldn't parse github url"

class GithubProject(object):

    def __init__(self, owner, project):
        self.owner = owner
        self.project = project

    @staticmethod
    def parse_url(url, do_soup=False):
        if "github.com/" in url:
            # shortcutting this due to urls being fairly predictable ;)
            (owner, project) = url.split('/')[3:5]
            return GithubProject( owner, project )
        elif False and "github.io/" in url:
            ## BLOCKING OUT - this may be an antipattern, instead treat as general non-GH url
            # someone.github.io/project
            urlbits = url.split('/')
            serverbits = urlbits[2].split('.')
            return GithubProject( serverbits[0], urlbits[3] )
        elif do_soup:
            # some non-github url, go fetch it and see if there's a github link
            try:
                req = requests.get(url)
                soop = BeautifulSoup(req.content, "html5lib")

                # if there's a class=github style link, take it!
                for link in soop.find_all('a', {'class','github'}):
                    current_link = link.get('href')
                    gh = GithubProject.parse_url(current_link, False)
                    if GithubProject.is_valid(gh):
                        return gh
                # otherwise, try every link and see if it has github in it
                for link in soop.find_all('a', href=re.compile("github.com/")):
                    current_link = link.get('href')
                    #assume the first valid link is likely to be the one referring to the project itself
                    gh = GithubProject.parse_url(current_link, False)
                    if GithubProject.is_valid(gh):
                        return gh
            except Exception as e:
                return None
        else:
            return None

    @staticmethod
    def is_valid(gh):
        if gh and hasattr(gh, 'owner') and hasattr(gh, 'project'):
            if gh.owner and gh.project:
                return True
        return False


    likely_license_names = ['LICENSE', 'LICENCE', 'COPYING']
    likely_license_exts = ['', '.txt', '.md', '.rst']
    def license_url(self):
        github_api_url = "https://api.github.com/repos/{}/{}/license".format(self.owner, self.project)
        headers = { "Accept": "application/vnd.github.drax-preview+json" }
        r = requests.get(github_api_url, headers=headers)
        j = r.json()
        if 'html_url' in j:
            license_url = j['html_url']
        else:
            # try some typical license names
            license_url = "unknown - likely license names weren't found"
            lic_found = False
            for fname in self.likely_license_names:
                if lic_found:
                    break
                for fext in self.likely_license_exts:
                    maybe_url = "https://github.com/{}/{}/blob/master/{}{}".format(self.owner, self.project, fname, fext)
                    r = requests.head(maybe_url)
                    if r:
                        license_url = maybe_url
                        lic_found = True
                        break
        return license_url





def main():
    parser = argparse.ArgumentParser(description="Read all installed packages from sys.path and list licenses.")
    parser.add_argument('--pkg', metavar='package', type=str, nargs='+',
                        help='Get license info only for the packages listed.')
    parser.add_argument('--do-soup', action='store_true',
                        help='Parse homepage to try to find license link.')
    args = parser.parse_args()
    vargs = vars(args)

    if 'pkg' in vargs:
        just_these_pkgs = vargs['pkg']

    for pip_obj in get_installed_distributions():
        if just_these_pkgs and pip_obj.project_name not in just_these_pkgs:
            continue

        installed_distribution = InstalledDistribution(pip_obj, vargs['do_soup'])
        print(installed_distribution)

if __name__ == "__main__":
    main()
