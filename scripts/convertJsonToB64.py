import base64
# -*- coding: utf-32 -*-

st = "🖤"

# str = '''{
#   "username": "mark__roudebush",
#   "post_id": "B2sfv8igp_H",
#   "shortcode": "B-NdHJvH6jx",
#   "direct_link": "https://www.instagram.com/p/B2sfv8igp_H",
#   "caption": "🖤Who could be so lucky? #contaxg2 #portra400",
#   "display_url": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/e35/70199965_547444809328714_8209873839849946748_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=pE8Qx0LYCBUAX8h2f-I&oh=8a47ed6be54e172f5e9079fb5a2ad121&oe=5EB90626",
#   "thumbnail_src": "https://scontent-sjc3-1.cdninstagram.com/v/t51.2885-15/sh0.08/e35/c90.0.899.899a/s640x640/70199965_547444809328714_8209873839849946748_n.jpg?_nc_ht=scontent-sjc3-1.cdninstagram.com&_nc_cat=110&_nc_ohc=pE8Qx0LYCBUAX8h2f-I&oh=920daea13a66cfb5293d58305a814c8b&oe=5EB9A089"
# }'''

print(base64.b64encode(st.encode()))

# OUTPUT

# ewogICJ1c2VybmFtZSI6ICJtYXJrX19yb3VkZWJ1c2giLAogICJwb3N0X2lkIjogIkIyc2Z2OGlncF9IIiwKICAic2hvcnRjb2RlIjogIkItTmRISnZINmp4IiwKICAiZGlyZWN0X2xpbmsiOiAiaHR0cHM6Ly93d3cuaW5zdGFncmFtLmNvbS9wL0Iyc2Z2OGlncF9IIiwKICAiY2FwdGlvbiI6ICLwn5akXG5XaG8gY291bGQgYmUgc28gbHVja3k/XG4jY29udGF4ZzIgI3BvcnRyYTQwMCIsCiAgImRpc3BsYXlfdXJsIjogImh0dHBzOi8vc2NvbnRlbnQtc2pjMy0xLmNkbmluc3RhZ3JhbS5jb20vdi90NTEuMjg4NS0xNS9lMzUvNzAxOTk5NjVfNTQ3NDQ0ODA5MzI4NzE0XzgyMDk4NzM4Mzk4NDk5NDY3NDhfbi5qcGc/X25jX2h0PXNjb250ZW50LXNqYzMtMS5jZG5pbnN0YWdyYW0uY29tJl9uY19jYXQ9MTEwJl9uY19vaGM9cEU4UXgwTFlDQlVBWDhoMmYtSSZvaD04YTQ3ZWQ2YmU1NGUxNzJmNWU5MDc5ZmI1YTJhZDEyMSZvZT01RUI5MDYyNiIsCiAgInRodW1ibmFpbF9zcmMiOiAiaHR0cHM6Ly9zY29udGVudC1zamMzLTEuY2RuaW5zdGFncmFtLmNvbS92L3Q1MS4yODg1LTE1L3NoMC4wOC9lMzUvYzkwLjAuODk5Ljg5OWEvczY0MHg2NDAvNzAxOTk5NjVfNTQ3NDQ0ODA5MzI4NzE0XzgyMDk4NzM4Mzk4NDk5NDY3NDhfbi5qcGc/X25jX2h0PXNjb250ZW50LXNqYzMtMS5jZG5pbnN0YWdyYW0uY29tJl9uY19jYXQ9MTEwJl9uY19vaGM9cEU4UXgwTFlDQlVBWDhoMmYtSSZvaD05MjBkYWVhMTNhNjZjZmI1MjkzZDU4MzA1YTgxNGM4YiZvZT01RUI5QTA4OSIKfQo =
