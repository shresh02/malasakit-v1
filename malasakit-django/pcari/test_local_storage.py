
from django.urls import reverse

import os

from pcari.selenium_utilities import AbstractSeleniumTestCase
import time
from .models import Comment, Respondent, QuantitativeQuestion

from random import randint

class PartialResponseSubmissionTestCase(AbstractSeleniumTestCase):
    """Partially completes a response, then starts a new one. The incomplete
    response should be uploaded to the db. Correctness is assumed (from unit
    tests and PageLoadTestCase)"""

    def flow(self):
        """Runs through the page, fills out responses but does NOT submit"""
        self.assertIn(reverse('pcari:landing'), self.driver.current_url)
        self.driver.find_element_by_id('next').click()

        self.assertIn(reverse('pcari:quantitative-questions'), self.driver.current_url)
        self.inputs['quantitative-questions'] = \
                            self.driver.quant_questions_random_responses()

        self.assertIn(reverse('pcari:rate-comments'), self.driver.current_url)
        self.inputs['rate-comments'] = \
                            self.driver.rate_comments_random_responses()
        self.driver.find_element_by_id('next').click()

        self.assertIn(reverse('pcari:qualitative-questions'), self.driver.current_url)
        self.inputs['qualitative-questions'] = \
                                self.driver.qual_questions_random_responses()
        self.driver.find_element_by_id('next').click()

        self.assertIn(reverse('pcari:personal-information'), self.driver.current_url)
        self.driver.get("%s%s" % (self.live_server_url,
                                  reverse('pcari:personal-information')))
        self.inputs['personal-info'] = self.driver.personal_info_random_responses()

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def test_partial_response(self):
        self.flow()
        # fill out all responses
        before = Respondent.objects.count()
        # clear log
        self.driver.get_log('browser')
        self.driver.get("%s%s" % (self.live_server_url,
                                  reverse("pcari:landing")))
        self.driver.find_element_by_id('next').click()
        time.sleep(0.5) # give the server time to receive the response and add to db

        after = Respondent.objects.count()
        self.assertEqual(Respondent.objects.count(), before + 1)


class PageUpdateTestCase(AbstractSeleniumTestCase):
    """While the client is online, it should serve the most up-to-date version of
    each view. """

    def flow(self):
        """Runs through the page, fills out responses but does NOT submit"""
        self.assertIn(reverse('pcari:landing'), self.driver.current_url)
        self.driver.find_element_by_id('next').click()

        self.assertIn(reverse('pcari:quantitative-questions'), self.driver.current_url)
        self.inputs['quantitative-questions'] = \
                            self.driver.quant_questions_random_responses()

        self.assertIn(reverse('pcari:rate-comments'), self.driver.current_url)
        self.inputs['rate-comments'] = \
                            self.driver.rate_comments_random_responses()
        self.driver.find_element_by_id('next').click()

        self.assertIn(reverse('pcari:qualitative-questions'), self.driver.current_url)
        self.inputs['qualitative-questions'] = \
                                self.driver.qual_questions_random_responses()
        self.driver.find_element_by_id('next').click()

        self.assertIn(reverse('pcari:personal-information'), self.driver.current_url)
        self.driver.get("%s%s" % (self.live_server_url,
                                  reverse('pcari:personal-information')))
        self.inputs['personal-info'] = self.driver.personal_info_random_responses()

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def test_view_update(self):
        self.driver.get("%s" % self.live_server_url)  # browser will cache all resources

        # read contents of base template file in, get ready to change
        lines = open('pcari/templates/base.html').readlines()
        # now rename the base template file
        os.rename("pcari/templates/base.html", "pcari/templates/base-temp.html")
        # create a new one
        f = open('pcari/templates/base.html', 'w')

        modified = False # did we even catch and modify a line in the new template?

        for l in lines:
            # THE LINE THAT WILL BE CHANGED IN TEST TEMPLATE
            if '<p id="footnote">' in l:
                f.write('<p id="footnote" changed="1">ASDFASDF')
                modified = True
            else:
                f.write(l)
        f.close()

        self.assertTrue(modified, "Template was not modified! Cannot test if views update")

        pages = [reverse('pcari:%s' % (url)) for url in
            ['landing', 'quantitative-questions', 'rate-comments',
            'qualitative-questions', 'personal-information',
            'peer-responses', 'end']]

        for page in pages:
            self.driver.get('%s%s' % (self.live_server_url, page))
            changed = self.driver.find_element_by_id("footnote").get_attribute("changed")
            self.assertNotEqual(changed, None)
            # make sure the changed tag appears in ALL views!



    def tearDown(self):
        """Teardown steps: run regardless of test success or failure"""
        os.rename('pcari/templates/base-temp.html', 'pcari/templates/base.html')


class refreshResourcesTestCase(AbstractSeleniumTestCase):
    """Tests if heavy resources (location data and comments) refresh after 12 hours.
    Spoofs time on the client. Checks for browser console log output indicating
    successful loading of location data and comments- do NOT change these!"""

    def test_refresh_resources(self):
        """Spoofs time by rewriting getCurrentTimestamp on the client, then
        refreshing resources. Checks log for indication that location data and
        comments were reloaded."""
        # go to first page
        self.driver.find_element_by_id('next').click()
        self.driver.get_log('browser') # purge log

        self.driver.execute_script("""getCurrentTimestamp = function() {
            return new Date().getTime() + 13*60*60*1000;
        } """)

        self.driver.execute_script("refreshResources()")
        time.sleep(0.5)
        log = self.driver.get_log("browser")
        self.assertTrue(any('location-data' in l['message'] for l in log))
        self.assertTrue(any('comments' in l['message'] for l in log))
