"""
Integration tests using Selenium.
Drawing inspiration from
https://docs.djangoproject.com/en/1.10/topics/testing/tools/#liveservertestcase

Tests to include:
- Loading and clicking through webpage
- Language works
- Changing language does not remove user input
- Bloom works
- LocalStorage is behaving correctly (online case)
- ServiceWorker is registered
- Clock stuff- throw system clock forward

Tests that we want but are not vital to functionality
- Proper mobile scaling (by testing with smaller window)

Tests that we want but are harder to implement as part of Django test suite:
- LocalStorage is behaving correctly (offline case)
- ServiceWorker works when offline

Architectural thoughts:
Writing multiple levels. Interfacing with a single UI element, responding to a question etc.
"""

from django.urls import reverse

from pcari.selenium_utilities import AbstractSeleniumTestCase
import time
from .models import Comment, Respondent, QuantitativeQuestion



class PageLoadTestCase(AbstractSeleniumTestCase):
    """Clickthrough test case, checks for page functionality and LocalStorage
    correctness."""


    # Methods for testing views. Each one should push inputs to corresponding
    # key in dictionary self.inputs.

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def landing(self):
        self.assertIn(reverse('pcari:landing'), self.driver.current_url)
        self.driver.find_element_by_id('next').click()

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def quant_questions(self):
        self.assertIn(reverse('pcari:quantitative-questions'), self.driver.current_url)
        self.inputs['quantitative-questions'] = \
                            self.driver.quant_questions_random_responses()

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def rate_comments(self):
        self.assertIn(reverse('pcari:rate-comments'), self.driver.current_url)
        self.inputs['rate-comments'] = \
                            self.driver.rate_comments_random_responses()

        self.driver.find_element_by_id('next').click()

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def qual_questions(self):
        self.assertIn(reverse('pcari:qualitative-questions'), self.driver.current_url)

        self.inputs['qualitative-questions'] = \
                                self.driver.qual_questions_random_responses()

        self.driver.find_element_by_id('next').click()

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def personal_info(self):
        self.assertIn(reverse('pcari:personal-information'), self.driver.current_url)

        self.driver.get("%s%s" % (self.live_server_url,
                                  reverse('pcari:personal-information')))

        self.inputs['personal-info'] = self.driver.personal_info_random_responses()


    def check_script_and_local_storage(self):
        """Final check before submission: look for any errors in JavaScript
        that didn't break flow, purge log, grab LocalStorage, and check
        its correctness (against randomized inputs)."""
        local_storage = self.driver.local_storage
        current_user = local_storage[local_storage['current']['data']]['data']

        print self.inputs
        print current_user
        # test quant question answers
        for k in current_user['question-ratings'].keys():
            i = int(k) - 1 # keys are 1-indexed and strings
            # score history is disabled for now, so just testing LS score
            # against final element in expected_list
            ls_score = current_user['question-ratings'][k]
            expected_list = self.inputs['quantitative-questions'][i] #pylint: disable=unsubscriptable-object
            self.assertEqual(ls_score, expected_list[-1],
                             """"question %s:
                expected %s but got %s""" % (k, expected_list[-1], ls_score))
            # self.assertListEqual(ls_list, expected_list,
            #                      msg="""Incorrect history on quant q %s (index
            #                      %s), expected %s but got %s""" % (k, i,
            #                                    expected_list, ls_list))

        # test that comment ratings are identical (hard to get comment ids from UI)
        ls_ratings = current_user['comment-ratings'].values()
        expected_ratings = [r[-1] for r in self.inputs['rate-comments']] #pylint: disable=not-an-iterable
        ls_ratings.sort()
        expected_ratings.sort()
        self.assertListEqual(ls_ratings, expected_ratings,
                             "expected %s, got %s" % (str(expected_ratings),
                                                      str(ls_ratings)))

        # test qual question answers
        for k in current_user['comments'].keys():
            comment = current_user['comments'][k]
            expected_comment = self.inputs['qualitative-questions'][k] #pylint: disable=unsubscriptable-object
            self.assertEqual(comment, expected_comment)

        # test personal info
        self.assertEqual(current_user['respondent-data']['province'],
                         self.inputs['personal-info']['province'])
        self.assertEqual(current_user['respondent-data']['age'],
                         self.inputs['personal-info']['age'])
        self.assertEqual(current_user['respondent-data']['city-or-municipality'],
                         self.inputs['personal-info']['city'])
        self.assertEqual(current_user['respondent-data']['barangay'],
                         self.inputs['personal-info']['barangay'])

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def submission(self):
        """Submits the response. """
        before = Respondent.objects.count()
        # click the next button, should pull up a popup
        self.driver.find_element_by_id('next').click()
        self.driver.find_element_by_id('submit').click()
        time.sleep(0.5) # give the server time to receive the response and add to db
        self.assertEqual(Respondent.objects.count(), before + 1)
        # we shouldn't need to test the correctness of the response in the db
        # because that is already tested in the views

    def test_flow_local_storage(self):
        """Clicks through views in appropriate order"""
        self.landing()
        self.quant_questions()
        self.rate_comments()
        self.qual_questions()
        self.personal_info()
        self.check_script_and_local_storage()
        self.submission()


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



class LanguageChangeTestCase(AbstractSeleniumTestCase):
    """Fills out responses, then accesses them again in both EN and TL, checking if
    they are preserved."""

    languages = ['tl', 'en']

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
    def test_quant_question_change(self):
        """Accesses quantitative questions field in EN and TL, checks if responses
        are the same."""
        self.flow()
        # number of clicks = num_questions - 1
        num_questions = QuantitativeQuestion.objects.count()
        for code in self.languages:
            scores = []
            self.driver.get("%s/%s/quantitative-questions/" % (self.live_server_url, code))
            for i in range(num_questions):
                slider = self.driver.find_element_by_css_selector('input[type=range]')
                score = int(slider.get_attribute('value'))
                # If skip message is shown, then the user skipped
                if self.driver.find_element_by_id("skip-notice").get_attribute("style") \
                   == "display: block;":
                    scores.append(-1)
                else:
                    scores.append(score)
                self.driver.find_element_by_id("previous").click()
            # remember, we're still recording score histories
            scores.reverse() # mutate the list, because we went backwards and want to flip
            self.assertListEqual(scores, [lst[-1] for lst in self.inputs['quantitative-questions']])

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def test_rate_comment_change(self):
        """Checks the rate comment view and makes sure the number of remaining comments
        is correct"""
        self.flow()
        expected_remaining = Comment.objects.count() - len(self.inputs['rate-comments'])

        for code in self.languages:
            self.driver.get("%s/%s/rate-comments/" % (self.live_server_url, code))
            client_remaining = len(self.driver.find_elements_by_tag_name('image'))
            self.assertEqual(client_remaining, expected_remaining)

    @AbstractSeleniumTestCase.dump_driver_log_on_error
    def test_qual_question_change(self):
        self.flow()
        expected_comments = self.inputs['qualitative-questions'].values() # list of comments

        for code in self.languages:
            self.driver.get("%s/%s/qualitative-questions/" % (self.live_server_url, code))
            self.driver.get_screenshot_as_file("qual-q-%s" % code)
            text_boxes = self.driver.find_elements_by_tag_name("textarea")
            client_comments = [box.get_attribute("value") for box in text_boxes]
            self.assertListEqual(client_comments, expected_comments)
