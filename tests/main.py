import os
from bs4 import BeautifulSoup
import requests
import json
import unittest

# url_one = 'https://www.instagram.com/googlecloud/'
# url_two = 'https://www.instagram.com/joshbloom/'
# url_three = 'https://www.instagram.com/explore/tags/googlecloud/'

# def processPosts(url):
#     page = requests.get(url)
#     soup = BeautifulSoup(page.content, 'html.parser')
#     scripts = soup.find_all('script')
#     print(scripts)

#     try:
#         data = scripts[4].getText()[21:-1]  # Clean out pre-amble
#         postList = json.loads(data)[
#             "entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]
#     except:
#         data = scripts[3].getText()[21:-1]  # Clean out pre-amble
#         postList = json.loads(data)[
#             "entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]

#     collection = getPosts(postList)
#     # print(json.dumps(collection, indent=2))
#     return json.dumps(collection, indent=2)


# def getPosts(postList):
#     postCollection = []
#     for post in postList:
#         item = {}
#         item["id"] = post["node"]["id"]
#         item["shortcode"] = post["node"]["shortcode"]
#         item["direct_link"] = "https://www.instagram.com/p" + \
#             post["node"]["shortcode"]
#         item["caption"] = post["node"]["edge_media_to_caption"]["edges"][0]["node"]["text"]
#         item["display_url"] = post["node"]["display_url"]
#         item["thumbnail_src"] = post["node"]["thumbnail_src"]
#         item["thumbnail_resources"] = post["node"]["thumbnail_resources"]
#         postCollection.append(item)
#     return postCollection


class TestInstaPuller(unittest.TestCase):

    def test_sum(self):
        self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")

    # def testInstaParserOne(self):
    #     self.assertTrue(processPosts(url_one))

    # def testInstaParserTwo(self):
    #     self.assertTrue(processPosts(url_two))

    # def testBadParse(self):
    #     with self.assertRaises(KeyError):
    #         processPosts(url_three)


if __name__ == '__main__':
    unittest.main()
