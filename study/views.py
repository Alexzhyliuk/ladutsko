from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from .decorators.is_admin import admin_only
from .decorators.is_teacher import teacher_only
from accounts.forms import UserEditForm, UserCreateForm
from accounts.models import Application
from .forms import AdminProfileEditForm, GroupForm, SubjectForm, LessonForm, AdminTestForm, QuestionForm, AnswerForm
from .models import Group, Subject, Lesson, LessonPhoto, Test, Question, Answer
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings


class IndexView(LoginRequiredMixin, View):
    menu = {
        "admin": {
            "Пользователи": {
                "Учителя": reverse_lazy("teachers"),
                "Ученики": reverse_lazy("students"),
            },
            "Заявки": reverse_lazy("applications"),
            "Группы": reverse_lazy("groups"),
            "Предметы": reverse_lazy("subjects"),
            "Уроки": reverse_lazy("lessons"),
            "Тесты": reverse_lazy("tests"),
        },
        "teacher": {
            "Моя группа": reverse_lazy("my-group"),
            "Предметы": "#",
            "Уроки": "#",
            "Тесты": "#",
        }
    }

    def get(self, request, *args, **kwargs):

        user = request.user
        if user.profile.type == 1:
            return render(request, "study/index.html", {"menu": self.menu["admin"]})
        if user.profile.type == 2:
            return render(request, "study/index.html", {"menu": self.menu["teacher"]})


@method_decorator(admin_only, name="dispatch")
class TeachersListView(LoginRequiredMixin, ListView):
    model = User
    context_object_name = "objects"
    template_name = "study/teachers.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(profile__type=2)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


@method_decorator(admin_only, name="dispatch")
class TeacherEditView(LoginRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        teacher = get_object_or_404(User, pk=pk)
        user_form = UserEditForm(instance=teacher, data=request.POST)
        profile_form = AdminProfileEditForm(instance=teacher.profile, data=request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.username = user.email
            user.save()

            group = profile_form.cleaned_data.get("group")
            profile = profile_form.save()

            if group.owner and group.owner != user:
                messages.error(request, f"У группы {group.name} уже есть учитель!")
                return redirect(reverse("teacher", kwargs={"pk": pk}))

            group.owner = profile.user
            group.save()

            messages.success(request, "Пользователь успешно изменен!")

        return redirect(reverse("teacher", kwargs={"pk": pk}))

    def get(self, request, pk, *args, **kwargs):
        teacher = get_object_or_404(User, pk=pk)
        user_form = UserEditForm(instance=teacher)
        profile_form = AdminProfileEditForm(instance=teacher.profile)

        teacher_group = teacher.study_groups.first()
        groups = Group.objects.all()

        return render(request, "study/teacher-edit.html", {
            "user_form": user_form,
            "profile_form": profile_form,
            "teacher_group": teacher_group,
            "groups": groups,
            "teacher": teacher,
        })


@method_decorator(admin_only, name="dispatch")
class TeacherCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user_form = UserCreateForm(request.POST)
        profile_form = AdminProfileEditForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():

            new_user = user_form.save(commit=False)
            new_user_password = user_form.cleaned_data.get("password")
            new_user.set_password(new_user_password)
            new_user.username = new_user.email
            new_user.save()

            profile = new_user.profile
            profile.middle_name = profile_form.cleaned_data.get("middle_name")
            profile.type = 2
            profile.save()

            group = profile_form.cleaned_data.get("group")
            if group:
                group.owner = new_user
                group.save()

            try:
                send_mail(
                    "Данные для входа",
                    f"Логин - ваша почта: {new_user.email}\nПароль: {new_user_password}",
                    settings.EMAIL_HOST_USER,
                    [new_user.email])
            except Exception as err:
                print(err)
                messages.error(request, "Не получилось отправить письмо на почту")

            messages.success(request, "Пользователь успешно создан!")
            return redirect(reverse("teachers"))

        return redirect(reverse("teacher-add"))

    def get(self, request, *args, **kwargs):
        user_form = UserCreateForm()
        profile_form = AdminProfileEditForm()
        groups = Group.objects.all()
        return render(request, "study/teacher-add.html", {
            "user_form": user_form,
            "profile_form": profile_form,
            "groups": groups,
        })


@admin_only
def delete_teacher(request, pk):

    teacher = get_object_or_404(User, pk=pk)
    username = teacher.username
    teacher.delete()
    messages.success(request, f"Учитель {username} удален!")

    return redirect(reverse("teachers"))


@method_decorator(admin_only, name="dispatch")
class StudentsListView(LoginRequiredMixin, ListView):
    model = User
    context_object_name = "objects"
    template_name = "study/students.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(profile__type=3)


@method_decorator(admin_only, name="dispatch")
class StudentEditView(LoginRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        student = get_object_or_404(User, pk=pk)
        user_form = UserEditForm(instance=student, data=request.POST)
        profile_form = AdminProfileEditForm(instance=student.profile, data=request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.username = user.email
            user.save()

            group = profile_form.cleaned_data.get("group")
            user_group = user.group_set.first()
            profile_form.save()

            if group:
                if not(user in group.students.all()):
                    if user_group:
                        user_group.students.remove(user)
                    group.students.add(user)
            else:
                if user_group:
                    user_group.students.remove(user)

            messages.success(request, "Пользователь успешно изменен!")

        return redirect(reverse("student", kwargs={"pk": pk}))

    def get(self, request, pk, *args, **kwargs):
        student = get_object_or_404(User, pk=pk)
        user_form = UserEditForm(instance=student)
        profile_form = AdminProfileEditForm(instance=student.profile)

        student_group = student.group_set.first()
        groups = Group.objects.all()

        return render(request, "study/student-edit.html", {
            "user_form": user_form,
            "profile_form": profile_form,
            "student_group": student_group,
            "groups": groups,
            "student": student,
        })


@method_decorator(admin_only, name="dispatch")
class StudentCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user_form = UserCreateForm(request.POST)
        profile_form = AdminProfileEditForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():

            new_user = user_form.save(commit=False)
            new_user_password = user_form.cleaned_data.get("password")
            new_user.set_password(new_user_password)
            new_user.username = new_user.email
            new_user.save()

            profile = new_user.profile
            profile.middle_name = profile_form.cleaned_data.get("middle_name")
            profile.type = 3
            profile.save()

            group = profile_form.cleaned_data.get("group")
            if group:
                group.students.add(new_user)

            try:
                send_mail(
                    "Данные для входа",
                    f"Логин - ваша почта: {new_user.email}\nПароль: {new_user_password}",
                    settings.EMAIL_HOST_USER,
                    [new_user.email])
            except Exception as err:
                print(err)
                messages.error(request, "Не получилось отправить письмо на почту")

            messages.success(request, "Пользователь успешно создан!")
            return redirect(reverse("students"))

        return redirect(reverse("student-add"))

    def get(self, request, *args, **kwargs):
        user_form = UserCreateForm()
        profile_form = AdminProfileEditForm()
        groups = Group.objects.all()
        return render(request, "study/student-add.html", {
            "user_form": user_form,
            "profile_form": profile_form,
            "groups": groups,
        })


@admin_only
def delete_student(request, pk):

    student = get_object_or_404(User, pk=pk)
    username = student.username
    student.delete()
    messages.success(request, f"Ученик {username} удален!")

    return redirect(reverse("students"))


@method_decorator(admin_only, name="dispatch")
class ApplicationsListView(LoginRequiredMixin, ListView):
    model = Application
    context_object_name = "objects"
    template_name = "study/applications.html"


@method_decorator(admin_only, name="dispatch")
class ApplicationView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        application = get_object_or_404(Application, pk=pk)
        user_form = UserCreateForm(initial={
            "first_name": application.first_name,
            "last_name": application.last_name,
            "email": application.email
        })
        profile_form = AdminProfileEditForm(initial={
            "middle_name": application.middle_name,
            "group": application.group_id
        })
        groups = Group.objects.all()

        if not(Group.objects.filter(id=application.group_id).first()):
            messages.error(request, "Пользователь указал несуществующую группу!")

        return render(request, "study/application.html", {
            "user_form": user_form,
            "profile_form": profile_form,
            "groups": groups,
            "application": application
        })


@admin_only
def delete_application(request, pk):

    application = get_object_or_404(Application, pk=pk)
    email = application.email
    application.delete()
    messages.success(request, f"Заявка от {email} удален!")

    return redirect(reverse("applications"))


@method_decorator(admin_only, name="dispatch")
class GroupsListView(LoginRequiredMixin, ListView):
    model = Group
    context_object_name = "objects"
    template_name = "study/group/list.html"


@method_decorator(admin_only, name="dispatch")
class GroupEditView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        group = get_object_or_404(Group, pk=pk)
        form = GroupForm(instance=group, data=request.POST)
        if form.is_valid():
            new_owner = form.cleaned_data.get("owner")

            if new_owner == group.owner:
                form.save()
            elif new_owner:
                if not (new_owner.study_groups.first()):
                    group = form.save(commit=False)
                    group.owner = new_owner
                    group.save()
                else:
                    form.save()
                    messages.error(
                        request,
                        f"Учитель {new_owner} уже является владельцем группы {new_owner.study_groups.first()}"
                    )
            else:
                group = form.save(commit=False)
                group.owner = None
                group.save()

            messages.success(request, "Группа успешно изменена!")
        return redirect(reverse("group", kwargs={"pk": pk}))

    def get(self, request, pk, *args, **kwargs):
        group = get_object_or_404(Group, pk=pk)
        form = GroupForm(instance=group)
        teachers = User.objects.filter(profile__type=2)

        return render(request, "study/group/edit.html", {"form": form, "group": group, "teachers": teachers})


@method_decorator(admin_only, name="dispatch")
class GroupCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = GroupForm(request.POST)
        if form.is_valid():
            owner = form.cleaned_data.get("owner")
            if owner:
                if owner.study_groups.first():
                    messages.error(request, f"Учитель {owner} уже владеет группой {owner.study_groups.first()}!")
                    return redirect(reverse("group-add"))
                new_group = form.save(commit=False)
                new_group.owner = owner
                new_group.save()
            else:
                form.save()

            messages.success(request, "Группа успешно создана!")

        return redirect(reverse("groups"))

    def get(self, request, *args, **kwargs):
        form = GroupForm()
        teachers = User.objects.filter(profile__type=2)
        return render(request, "study/group/add.html", {"form": form, "teachers": teachers})


@admin_only
def delete_group(request, pk):

    group = get_object_or_404(Group, pk=pk)
    name = group.name
    group.delete()
    messages.success(request, f"Группа {name} удалена!")

    return redirect(reverse("groups"))


@method_decorator(admin_only, name="dispatch")
class SubjectsListView(LoginRequiredMixin, ListView):
    model = Subject
    context_object_name = "objects"
    template_name = "study/subjects/list.html"


@method_decorator(admin_only, name="dispatch")
class SubjectEditView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        subject = get_object_or_404(Subject, pk=pk)
        form = SubjectForm(instance=subject, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Предмет успешно изменен")

        return redirect(reverse("subject", kwargs={"pk": pk}))

    def get(self, request, pk, *args, **kwargs):
        subject = get_object_or_404(Subject, pk=pk)
        form = SubjectForm(instance=subject)
        groups = Group.objects.all()
        return render(request, "study/subjects/edit.html", {"form": form, "subject": subject, "groups": groups})


@method_decorator(admin_only, name="dispatch")
class SubjectCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = SubjectForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Предмет успешно создан")

        return redirect(reverse("subjects"))

    def get(self, request, *args, **kwargs):
        form = SubjectForm()
        groups = Group.objects.all()
        return render(request, "study/subjects/add.html", {"form": form, "groups": groups})


@admin_only
def delete_subject(request, pk):

    subject = get_object_or_404(Subject, pk=pk)
    name = subject.name
    subject.delete()
    messages.success(request, f"Предмет {name} удален!")

    return redirect(reverse("subjects"))


@method_decorator(admin_only, name="dispatch")
class LessonsListView(LoginRequiredMixin, ListView):
    model = Lesson
    context_object_name = "objects"
    template_name = "study/lesson/list.html"


@method_decorator(admin_only, name="dispatch")
class LessonEditView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(Lesson, pk=pk)
        form = LessonForm(instance=lesson, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Урок изменен!")
        return redirect(reverse("lesson", kwargs={"pk": pk}))

    def get(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(Lesson, pk=pk)
        form = LessonForm(instance=lesson)
        subjects = Subject.objects.all()
        tests = Test.objects.all()
        photos = LessonPhoto.objects.filter(owner=lesson.subject.group.owner)

        return render(request, "study/lesson/edit.html", {
            "form": form,
            "lesson": lesson,
            "subjects": subjects,
            "tests": tests,
            "photos": photos
        })


@method_decorator(admin_only, name="dispatch")
class LessonCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = LessonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Урок создан!")
        return redirect(reverse("lessons"))

    def get(self, request, *args, **kwargs):

        form = LessonForm()
        subjects = Subject.objects.all()
        tests = Test.objects.all()
        photos = LessonPhoto.objects.all()

        return render(request, "study/lesson/add.html", {
            "form": form,
            "subjects": subjects,
            "tests": tests,
            "photos": photos
        })


@admin_only
def delete_lesson(request, pk):

    lesson = get_object_or_404(Lesson, pk=pk)
    name = lesson.name
    lesson.delete()
    messages.success(request, f"Урок {name} удален!")

    return redirect(reverse("lessons"))


@method_decorator(admin_only, name="dispatch")
class TestsListView(LoginRequiredMixin, ListView):
    model = Test
    context_object_name = "objects"
    template_name = "study/test/list.html"


@method_decorator(admin_only, name="dispatch")
class TestEditView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        test = get_object_or_404(Test, pk=pk)
        form = AdminTestForm(instance=test, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Тест изменен!")
        return redirect(reverse("test", kwargs={"pk": pk}))

    def get(self, request, pk, *args, **kwargs):
        test = get_object_or_404(Test, pk=pk)
        form = AdminTestForm(instance=test)
        teachers = User.objects.filter(profile__type=2)

        return render(request, "study/test/edit.html", {
            "form": form,
            "test": test,
            "teachers": teachers,
        })


@method_decorator(admin_only, name="dispatch")
class TestCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = AdminTestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Тест создан!")
        return redirect(reverse("tests"))

    def get(self, request, *args, **kwargs):
        form = AdminTestForm()
        teachers = User.objects.filter(profile__type=2)

        return render(request, "study/test/add.html", {
            "form": form,
            "teachers": teachers,
        })


@admin_only
def delete_test(request, pk):

    test = get_object_or_404(Test, pk=pk)
    name = test.name
    test.delete()
    messages.success(request, f"Тест {name} удален!")

    return redirect(reverse("tests"))


@method_decorator(admin_only, name="dispatch")
class TestQuestionCreateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        form = QuestionForm(request.POST)
        if form.is_valid():
            new_question = form.save(commit=False)
            new_question.test = get_object_or_404(Test, pk=pk)
            new_question.save()
            messages.success(request, "Вопрос создан!")

        return redirect(reverse("test", kwargs={"pk": pk}))

    def get(self, request, *args, **kwargs):
        form = QuestionForm()
        return render(request, "study/test/question-add.html", {
            "form": form,
            "types": Question.Type.choices
        })


@admin_only
def delete_question(request, test_pk, question_pk):

    question = get_object_or_404(Question, pk=question_pk)
    name = question.text
    question.delete()
    messages.success(request, f"Вопрос {name} удален!")

    return redirect(reverse("test", kwargs={"pk": test_pk}))


@method_decorator(admin_only, name="dispatch")
class TestQuestionEditView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        question = get_object_or_404(Question, pk=kwargs["question_pk"])
        form = QuestionForm(instance=question, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Вопрос изменен!")

        return redirect(reverse("test-question", kwargs=kwargs))

    def get(self, request, *args, **kwargs):
        question = get_object_or_404(Question, pk=kwargs["question_pk"])
        form = QuestionForm(instance=question)
        answer_form = AnswerForm()
        return render(request, "study/test/question.html", {
            "form": form,
            "answer_form": answer_form,
            "question": question,
        })


@admin_only
def add_answer_variant(request, pk):
    if request.method == "POST":
        question = get_object_or_404(Question, pk=pk)
        form = AnswerForm(request.POST)
        if form.is_valid():
            new_answer = form.save(commit=False)
            new_answer.question = question
            new_answer.save()
            messages.success(request, "Добавлен вариант ответа")

        return redirect(reverse("test-question", kwargs={"question_pk": pk, "test_pk": question.test.pk}))
    else:
        return redirect(reverse("tests"))


@admin_only
def add_correct_text_answer(request, pk):
    if request.method == "POST":
        question = get_object_or_404(Question, pk=pk)
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = question.answers.first()
            if answer:
                answer.text = form.cleaned_data.get("text")
                answer.save()
                messages.success(request, "Правильный ответ изменен")
            else:
                new_answer = form.save(commit=False)
                new_answer.question = question
                new_answer.save()
                messages.success(request, "Правильный ответ добавлен")

        return redirect(reverse("test-question", kwargs={"question_pk": pk, "test_pk": question.test.pk}))
    else:
        return redirect(reverse("tests"))


@admin_only
def delete_answer(request, pk):

    answer = get_object_or_404(Answer, pk=pk)
    name = answer.text
    answer.delete()
    messages.success(request, f"Ответ {name} удален!")

    return HttpResponse("Answer delete successfully!")


@method_decorator(teacher_only, name="dispatch")
class MyGroupListView(LoginRequiredMixin, ListView):
    model = User
    context_object_name = "objects"
    template_name = "study/teacher/my_group.html"

    def get_queryset(self):
        group = self.request.user.study_groups.first()
        if group:
            students = group.students.all()
            return students
        return []


@method_decorator(teacher_only, name="dispatch")
class MyGroupCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = GroupForm(request.POST)
        if form.is_valid():
            new_group = form.save(commit=False)
            new_group.owner = request.user
            new_group.save()
            messages.success(request, "Ваша группа создана!")
            return redirect(reverse("my-group"))

        return redirect(reverse("my-group-create"))

    def get(self, request, *args, **kwargs):
        form = GroupForm()
        return render(request, "study/teacher/create-group.html", {"form": form})


def exclude_student(request, pk):
    student = get_object_or_404(User, pk=pk)
    group = request.user.study_groups.first()
    group.students.remove(student)
    messages.success(request, "Ученик был исключен")
    return redirect(reverse("my-group"))
