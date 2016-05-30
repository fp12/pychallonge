from __future__ import print_function
import datetime
import os
import random
import string
import unittest
import challonge
from challonge import Account, ChallongeException


username = None
api_key = None


def _get_random_name():
    return "pychallonge_" + "".join(random.choice(string.ascii_lowercase) for _ in range(0, 15))


class AccountTestCase(unittest.TestCase):

    def test_init(self):
        _account = Account(username, api_key)
        self.assertEqual(_account._user, username)
        self.assertEqual(_account._api_key, api_key)

    def test_call(self):
        _account = Account(username, api_key)
        self.assertNotEqual(_account.fetch("GET", "tournaments"), '')


class TournamentsTestCase(unittest.TestCase):

    def setUp(self):
        self._account = Account(username, api_key)
        self.random_name = _get_random_name()

        self.t = self._account.tournaments.create(self.random_name, self.random_name)

    def tearDown(self):
        self._account.tournaments.destroy(self.t["id"])

    def test_index(self):
        ts = self._account.tournaments.index()
        ts = list(filter(lambda x: x["id"] == self.t["id"], ts))
        self.assertEqual(len(ts), 1)
        self.assertEqual(self.t, ts[0])

    def test_index_filter_by_state(self):
        ts = self._account.tournaments.index(state="pending")
        ts = list(filter(lambda x: x["id"] == self.t["id"], ts))
        self.assertEqual(len(ts), 1)
        self.assertEqual(self.t, ts[0])

        ts = self._account.tournaments.index(state="in_progress")
        ts = list(filter(lambda x: x["id"] == self.t["id"], ts))
        self.assertEqual(ts, [])

    def test_index_filter_by_created(self):
        ts = self._account.tournaments.index(
            created_after=datetime.datetime.now().date() - datetime.timedelta(days=1))
        ts = filter(lambda x: x["id"] == self.t["id"], ts)
        self.assertTrue(self.t["id"] in map(lambda x: x["id"], ts))

    def test_show(self):
        self.assertEqual(self._account.tournaments.show(self.t["id"]),
                         self.t)

    def test_update_name(self):
        self._account.tournaments.update(self.t["id"], name="Test!")

        t = self._account.tournaments.show(self.t["id"])

        self.assertEqual(t["name"], "Test!")
        t.pop("name")
        self.t.pop("name")

        self.assertTrue(t["updated-at"] >= self.t["updated-at"])
        t.pop("updated-at")
        self.t.pop("updated-at")

        self.assertEqual(t, self.t)

    def test_update_private(self):
        self._account.tournaments.update(self.t["id"], private=True)

        t = self._account.tournaments.show(self.t["id"])

        self.assertEqual(t["private"], True)

    def test_update_type(self):
        self._account.tournaments.update(self.t["id"], tournament_type="round robin")

        t = self._account.tournaments.show(self.t["id"])

        self.assertEqual(t["tournament-type"], "round robin")

    def test_start(self):
        # we have to add participants in order to start()
        self.assertRaises(
            ChallongeException,
            self._account.tournaments.start,
            self.t["id"])

        self.assertEqual(self.t["started-at"], None)

        self._account.participants.create(self.t["id"], "#1")
        self._account.participants.create(self.t["id"], "#2")

        self._account.tournaments.start(self.t["id"])

        t = self._account.tournaments.show(self.t["id"])
        self.assertNotEqual(t["started-at"], None)

    def test_finalize(self):
        self._account.participants.create(self.t["id"], "#1")
        self._account.participants.create(self.t["id"], "#2")

        self._account.tournaments.start(self.t["id"])
        ms = self._account.matches.index(self.t["id"])
        self.assertEqual(ms[0]["state"], "open")

        self._account.matches.update(
            self.t["id"],
            ms[0]["id"],
            scores_csv="3-2,4-1,2-2",
            winner_id=ms[0]["player1-id"])

        self._account.tournaments.finalize(self.t["id"])
        t = self._account.tournaments.show(self.t["id"])

        self.assertNotEqual(t["completed-at"], None)

    def test_reset(self):
        # have to add participants in order to start()
        self._account.participants.create(self.t["id"], "#1")
        self._account.participants.create(self.t["id"], "#2")

        self._account.tournaments.start(self.t["id"])

        # we can't add participants to a started tournament...
        self.assertRaises(
            ChallongeException,
            self._account.participants.create,
            self.t["id"],
            "name")

        self._account.tournaments.reset(self.t["id"])

        # but we can add participants to a reset tournament
        p = self._account.participants.create(self.t["id"], "name")

        self._account.participants.destroy(self.t["id"], p["id"])


class ParticipantsTestCase(unittest.TestCase):

    def setUp(self):
        self._account = Account(username, api_key)
        self.t_name = _get_random_name()

        self.t = self._account.tournaments.create(self.t_name, self.t_name)
        self.p1_name = _get_random_name()
        self.p1 = self._account.participants.create(self.t["id"], self.p1_name)
        self.p2_name = _get_random_name()
        self.p2 = self._account.participants.create(self.t["id"], self.p2_name)

    def tearDown(self):
        self._account.tournaments.destroy(self.t["id"])

    def test_index(self):
        ps = self._account.participants.index(self.t["id"])
        self.assertEqual(len(ps), 2)

        self.assertTrue(self.p1 == ps[0] or self.p1 == ps[1])
        self.assertTrue(self.p2 == ps[0] or self.p2 == ps[1])

    def test_show(self):
        p1 = self._account.participants.show(self.t["id"], self.p1["id"])
        self.assertEqual(p1["id"], self.p1["id"])

    def test_bulk_add(self):
        ps_names = [_get_random_name(), _get_random_name()]
        misc = ["test_bulk1", "test_bulk2"]

        ps = self._account.participants.bulk_add(self.t["id"], ps_names, misc=misc)
        self.assertEqual(len(ps), 2)

        self.assertTrue(ps_names[0] == ps[0]["name"] or ps_names[0] == ps[1]["name"])
        self.assertTrue(ps_names[1] == ps[0]["name"] or ps_names[1] == ps[1]["name"])

        self.assertTrue(misc[0] == ps[0]["misc"] or misc[0] == ps[1]["misc"])
        self.assertTrue(misc[1] == ps[0]["misc"] or misc[1] == ps[1]["misc"])

    def test_update(self):
        self._account.participants.update(self.t["id"], self.p1["id"], misc="Test!")
        p1 = self._account.participants.show(self.t["id"], self.p1["id"])

        self.assertEqual(p1["misc"], "Test!")
        self.p1.pop("misc")
        p1.pop("misc")

        self.assertTrue(p1["updated-at"] >= self.p1["updated-at"])
        self.p1.pop("updated-at")
        p1.pop("updated-at")

        self.assertEqual(self.p1, p1)

    def test_randomize(self):
        # randomize has a 50% chance of actually being different than
        # current seeds, so we're just verifying that the method runs at all
        self._account.participants.randomize(self.t["id"])


class MatchesTestCase(unittest.TestCase):

    def setUp(self):
        self._account = Account(username, api_key)
        self.t_name = _get_random_name()

        self.t = self._account.tournaments.create(self.t_name, self.t_name)
        self.p1_name = _get_random_name()
        self.p1 = self._account.participants.create(self.t["id"], self.p1_name)
        self.p2_name = _get_random_name()
        self.p2 = self._account.participants.create(self.t["id"], self.p2_name)
        self._account.tournaments.start(self.t["id"])

    def tearDown(self):
        self._account.tournaments.destroy(self.t["id"])

    def test_index(self):
        ms = self._account.matches.index(self.t["id"])

        self.assertEqual(len(ms), 1)
        m = ms[0]

        ps = set((self.p1["id"], self.p2["id"]))
        self.assertEqual(ps, set((m["player1-id"], m["player2-id"])))
        self.assertEqual(m["state"], "open")

    def test_show(self):
        ms = self._account.matches.index(self.t["id"])
        for m in ms:
            self.assertEqual(m, self._account.matches.show(self.t["id"], m["id"]))

    def test_update(self):
        ms = self._account.matches.index(self.t["id"])
        m = ms[0]
        self.assertEqual(m["state"], "open")

        self._account.matches.update(
            self.t["id"],
            m["id"],
            scores_csv="3-2,4-1,2-2",
            winner_id=m["player1-id"])

        m = self._account.matches.show(self.t["id"], m["id"])
        self.assertEqual(m["state"], "complete")


if __name__ == "__main__":
    username = os.environ.get("CHALLONGE_USER") if username == None else username
    api_key = os.environ.get("CHALLONGE_KEY") if api_key == None else api_key
    if not username or not api_key:
        raise RuntimeError("You must add CHALLONGE_USER and CHALLONGE_KEY \
            to your environment variables to run the test suite")

    unittest.main()
