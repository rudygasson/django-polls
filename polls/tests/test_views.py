import datetime

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model

from ..models import Question, Choice

def create_question(question_text, days, number_of_choices=3):
    """
    Create a question with the given `question_text` and published the
    given number of `days` offset to now (negative for questions published
    in the past, positive for questions that have yet to be published).
    """
    time = timezone.now() + datetime.timedelta(days=days)
    question = Question.objects.create(question_text=question_text, pub_date=time)
    for choice in range(1, number_of_choices + 1):
        Choice.objects.create(question=question, choice_text=f'Choice {choice}')
    return question

def login_as_admin(self):
    User = get_user_model()
    self.admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='password'
    )
    self.client.login(username='admin', password='password')

class QuestionIndexViewTests(TestCase):
    def test_no_questions(self):
        """
        If no questions exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        """
        Questions with a pub_date in the past and at least 2 choices
        are displayed on the index page.
        """
        question = create_question(question_text="Past Question", days=-2)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_future_question(self):
        """
        Questions with a pub_date in the future aren't displayed on
        the index page.
        """
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_future_question_as_admin(self):
        """
        Questions with a pub_date in the future are only displayed on
        the index page if the user is logged in as admin.
        """
        create_question(question_text="Future question.", days=30)
        login_as_admin(self)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "Future question.")
        self.assertEqual(response.context["latest_question_list"].count(), 1)

    def test_future_question_and_past_question(self):
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_two_past_questions(self):
        """
        The questions index page may display multiple questions, sorted by most recent date.
        """
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question2, question1],
        )

    def test_question_without_choices(self):
        """
        Questions with no choices are not displayed on the index page.
        """
        question = create_question(question_text="Past Question", days=-2, number_of_choices=0)
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:detail", args=(future_question.id,)) # type: ignore
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text="Past Question", days=-5)
        url = reverse("polls:detail", args=(past_question.id,)) # type: ignore
        response = self.client.get(url)
        self.assertContains(response, "Past Question")

class QuestionResultsViewTests(TestCase):
    def test_future_question(self):
        """
        The results view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:results", args=(future_question.id,)) # type: ignore
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The results view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text="Past Question", days=-5)
        url = reverse("polls:results", args=(past_question.id,)) # type: ignore
        response = self.client.get(url)
        self.assertContains(response, "Past Question")

    def test_vote_counting(self):
        """
        After voting for a choice, the vote counter for this choice
        is incremented and shown in the results view.
        """
        question = create_question(question_text="Test the vote", days=-2)
        url = reverse("polls:vote", args=(question.id,)) # type: ignore
        choice = { 'choice': 2 }
        response = self.client.post(url, data=choice)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('polls:results', args=(question.id,)))  # type: ignore
        self.assertEqual(str(question.choice_set.get(pk=choice['choice'])), "Choice 2") # type: ignore

    def test_vote_missing(self):
        """
        If no vote is submitted, the server responds with a 422 status and
        returns the same form with an error message.
        """
        question = create_question(question_text="Test the vote", days=-2)
        url = reverse("polls:vote", args=(question.id,)) # type: ignore
        response = self.client.post(url, data={})
        self.assertContains(response, "select a choice.", status_code=422)
