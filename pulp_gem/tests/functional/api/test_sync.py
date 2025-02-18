# coding=utf-8
"""Tests that sync gem plugin repositories."""
import unittest

from pulp_smash import api, config
from pulp_smash.exceptions import TaskReportError
from pulp_smash.pulp3.utils import gen_repo, get_added_content_summary, get_content_summary, sync

from pulp_gem.tests.functional.constants import (
    GEM_FIXTURE_SUMMARY,
    GEM_INVALID_FIXTURE_URL,
    GEM_REMOTE_PATH,
    GEM_REPO_PATH,
)
from pulp_gem.tests.functional.utils import gen_gem_remote
from pulp_gem.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class BasicSyncTestCase(unittest.TestCase):
    """Sync a repository with the gem plugin."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    def test_sync(self):
        """Sync repositories with the gem plugin.

        In order to sync a repository a remote has to be associated within
        this repository. When a repository is created this version field is set
        as None. After a sync the repository version is updated.

        Do the following:

        1. Create a repository, and a remote.
        2. Assert that repository version is None.
        3. Sync the remote.
        4. Assert that repository version is not None.
        5. Assert that the correct number of units were added and are present
           in the repo.
        6. Sync the remote one more time.
        7. Assert that repository version is different from the previous one.
        8. Assert that the same number of are present and that no units were
           added.
        """
        repo = self.client.post(GEM_REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        body = gen_gem_remote()
        remote = self.client.post(GEM_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["pulp_href"])

        # Sync the repository.
        self.assertIsNotNone(repo["latest_version_href"])
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["pulp_href"])

        self.assertIsNotNone(repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), GEM_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo), GEM_FIXTURE_SUMMARY)

        # Sync the repository again.
        latest_version_href = repo["latest_version_href"]
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["pulp_href"])

        self.assertEqual(latest_version_href, repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), GEM_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo), GEM_FIXTURE_SUMMARY)


class SyncInvalidTestCase(unittest.TestCase):
    """Sync a repository with a given url on the remote."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    def test_invalid_url(self):
        """Sync a repository using a remote url that does not exist.

        Test that we get a task failure. See :meth:`do_test`.
        """
        context = self.do_test("http://i-am-an-invalid-url.com/invalid/")
        self.assertIsNotNone(context.exception.task["error"]["description"])

    # Provide an invalid repository and specify keywords in the anticipated error message
    @unittest.skip("FIXME: Plugin writer action required.")
    def test_invalid_plugin_template_content(self):
        """Sync a repository using an invalid plugin_content repository.

        Assert that an exception is raised, and that error message has
        keywords related to the reason of the failure. See :meth:`do_test`.
        """
        context = self.do_test(GEM_INVALID_FIXTURE_URL)
        for key in ("mismached", "empty"):
            self.assertIn(key, context.exception.task["error"]["description"])

    def do_test(self, url):
        """Sync a repository given ``url`` on the remote."""
        repo = self.client.post(GEM_REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        body = gen_gem_remote(url=url)
        remote = self.client.post(GEM_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["pulp_href"])

        with self.assertRaises(TaskReportError) as context:
            sync(self.cfg, remote, repo)
        return context
