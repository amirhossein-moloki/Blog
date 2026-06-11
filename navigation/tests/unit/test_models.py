from django.test import TestCase

from navigation.models import Menu


class MenuModelTest(TestCase):
    def test_menu_creation(self):
        menu = Menu.objects.create(name="Main", location="header")
        self.assertEqual(str(menu), "Main")
