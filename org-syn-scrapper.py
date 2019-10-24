#! /usr/bin/env python3

# Copyright 2019 Karsten Lehmann <mail@kalehmann.de>

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This script provides functionality to scrape all the PDF links from the site
http://orgsyn.org/ and download the PDF files.
"""

from bs4 import BeautifulSoup, Tag
import requests
from typing import List
import urllib.parse

class OrgSynScrapper(object):
    ANNUAL_VOLUME_SELECT_ID = "ctl00_QuickSearchAnnVolList1"
    PAGES_RESPONSE_OPTIONS_INDEX = 11
    PAGES_RESPONSE_VIEWSTATE_INDEX = 51
    PAGES_RESPONSE_VIEWSTATEGENERATOR_INDEX = 55
    PAGES_RESPONSE_EVENTVALIDATION_INDEX = 59
    URL = "http://orgsyn.org"
    USER_AGENT = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"

    def __init__(self):
        self.session = None
        # The __VIEWSTATE value of OrgSyns formular
        self.viewstate = None
        # The __VIEWSTATEGENERATOR value of OrgSyns formular
        self.viewstategenerator = None
        # The __EVENTVALIDATION value of OrgSyns formular
        self.eventvalidation = None

    def __enter__(self) -> 'OrgSynScrapper':
        self.session = requests.session()
        self.session.headers.update({
	        "User-Agent" : OrgSynScrapper.USER_AGENT,
            "Accept" : "*/*",
            "Accept-Encoding" : "gzip,deflate,sdch",
            "Accept-Language" : "en-US,en;q=0.8",
        })

        return self

    def __exit__(self, type, value, traceback):
        self.session.close()

    @staticmethod
    def getInputValue(soup : BeautifulSoup, id : str) -> str:
        """Gets the value of the input element with the given id.

        :param soup: The BeautifulSoup instance to search for a input element
        with the given id
        :param id: The id of the input element

        :return: The value of the input element
        """
        input_el = soup.find('input', {"id" : id})
        if input_el:
            return input_el['value']
        return None

    @staticmethod
    def pdfLinkFilter(tag : Tag):
        """Filter for a BeautifulSoup instance for tags with a link to a pdf
        file in a folder named `Content`

        :param tag: The tag to check for a pdf link

        :returns: True if the tag links to a pdf file in a folder named Content
        else False
        """
        return (tag.has_attr("href") and tag["href"].startswith("Content")
            and tag["href"].endswith(".pdf"))

    def requestVolumes(self) -> List[str]:
        """Requests all annual volumes and sets the viewstate,
        viewstategenerator and eventvalidation attributes.

        :return: A list with all annual volumes as strings
        """
        response = self.session.get(OrgSynScrapper.URL)
        soup = BeautifulSoup(response.content, 'html.parser')

        self.viewstate = OrgSynScrapper.getInputValue(soup, "__VIEWSTATE")
        self.viewstategenerator = OrgSynScrapper.getInputValue(
            soup,
            "__VIEWSTATEGENERATOR"
        )
        self.eventvalidation = OrgSynScrapper.getInputValue(
            soup,
            "__EVENTVALIDATION"
        )

        annualVolSelect = soup.find(
            "select",
            {"id" : OrgSynScrapper.ANNUAL_VOLUME_SELECT_ID}
        )

        annualVolumes = map(
            lambda option: option["value"],
            annualVolSelect.findAll("option")
        )

        filtered_volumes = filter(
            lambda volume: volume,
            annualVolumes
        )

        return list(filtered_volumes)

    def requestPagesOfVolume(self, volume: str) -> List[str]:
        """Requests all pages of an annual volume.

        :param volume: The volume to request the pages for

        :return: A list with all the pages of the volume as strings
        """
        body = {
            "ctl00$ScriptManager1": "ctl00$UpdatePanel1|ctl00$QuickSearchAnnVolList1",
            "ctl00$QuickSearchAnnVolList1" : volume,
            "ctl00$tab2_TextBox": "",
            "ctl00$TBWE3_ClientState": "",
            "ctl00$SrcType": "Anywhere",
            "ctl00$MainContent$QSAnnVol": "Select Ann. Volume",
            "ctl00$MainContent$QSCollVol": "Select Coll. Volume",
            "ctl00$MainContent$searchplace": "publicationRadio",
            "ctl00$MainContent$TextQuickSearch": "",
            "ctl00$MainContent$TBWE2_ClientState": "",
            "ctl00$MainContent$SearchStructure": "",
            "ctl00$MainContent$SearchStructureMol": "",
            "ctl00$HidSrcType": "",
            "ctl00$WarningAccepted": "0",
            "ctl00$Direction": "",
            "__LASTFOCUS": "",
            "__EVENTTARGET": "ctl00$QuickSearchAnnVolList1",
            "__EVENTARGUMENT": "",
            "__ASYNCPOST": "true",
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategenerator,
            "__EVENTVALIDATION": self.eventvalidation,
        }

        response = self.session.post(OrgSynScrapper.URL, data=body)
        content = str(response.content)
        options_html = str(response.content).split("|")[
            OrgSynScrapper.PAGES_RESPONSE_OPTIONS_INDEX
        ]
        optionsSoup = BeautifulSoup(options_html, "html.parser")
        pages = map(
            lambda option: option["value"],
            optionsSoup.findAll("option")
        )
        filtered_pages = filter(
            lambda page: page,
            pages
        )

        self.viewstate = str(response.content).split("|")[
            OrgSynScrapper.PAGES_RESPONSE_VIEWSTATE_INDEX
        ]
        self.viewstategenerator = str(response.content).split("|")[
            OrgSynScrapper.PAGES_RESPONSE_VIEWSTATEGENERATOR_INDEX
        ]
        self.eventvalidation = str(response.content).split("|")[
            OrgSynScrapper.PAGES_RESPONSE_EVENTVALIDATION_INDEX
        ]

        return list(filtered_pages)

    def requestVolumePagePdfLinks(self, volume : str, page : str) -> List[str]:
        """Request all pdf links for a page of a volume.

        :param volume: The volume
        :param page: The page of the volume to request the pdf links for

        :return: A list with all the pdf links as strings
        """
        body = {
            "ctl00$QuickSearchAnnVolList1": volume,
            "ctl00$PageTextBoxDrop": page,
            "ctl00$tab2_TextBox": "",
            "ctl00$TBWE3_ClientState": "",
            "ctl00$SrcType": "Anywhere",
            "ctl00$MainContent$QSAnnVol": "Select Ann. Volume",
            "ctl00$MainContent$QSCollVol": "Select Coll. Volume",
            "ctl00$MainContent$searchplace": "publicationRadio",
            "ctl00$MainContent$TextQuickSearch": "",
            "ctl00$MainContent$TBWE2_ClientState": "",
            "ctl00$MainContent$SearchStructure": "",
            "ctl00$MainContent$SearchStructureMol": "",
            "ctl00$HidSrcType": "Citation",
            "ctl00$WarningAccepted": "1",
            "ctl00$Direction": "",
            "__LASTFOCUS": "",
            "__EVENTTARGET": "QuickSearchVolSrc",
            "__EVENTARGUMENT": "submitsearch",
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategenerator,
            "__EVENTVALIDATION": self.eventvalidation,
        }

        response = self.session.post(
            OrgSynScrapper.URL,
            data=body,
            cookies={"quickSearchTab" : "0"}
        )
        soup = BeautifulSoup(response.content, "html.parser")
        link_tags = soup.find_all(OrgSynScrapper.pdfLinkFilter)

        links = map(
            lambda tag: urllib.parse.urljoin(OrgSynScrapper.URL, tag["href"]),
            link_tags
        )

        return list(links)

if __name__ == "__main__":
    with OrgSynScrapper() as scrapper:
        pass
