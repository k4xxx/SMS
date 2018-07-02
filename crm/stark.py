# stark注册

from stark.service import stark
from crm import models
from stark.service.stark import DeFaultConfigClass
from django.utils.safestring import mark_safe
from django.conf.urls import url
from django.shortcuts import redirect,render,HttpResponse
from django.http import JsonResponse
import datetime
from django.db.models import Q


class ClassConfig(DeFaultConfigClass):
    def class_name(self,obj=None,is_header=False):
        if is_header:
            return '班级名称'
        return '%s(%s期)'%(obj.course,obj.semester)

    def get_teachers(self,obj=None,is_header=False):
        if is_header:
            return '任课老师'
        temp = []
        for o in obj.teachers.all():
            temp.append('<a href="delete_teacher/%s/%s" style="border:1px solid #369;padding:3px;margin-right:3px">%s</a>'%(obj.pk,o.pk,str(o)))
        return mark_safe(''.join(temp))

    def delete_class_teacher(self,request,class_id,teacher_id):
        class_obj = models.ClassList.objects.filter(pk=class_id).first()
        class_obj.teachers.remove(teacher_id)
        return redirect(self.get_list_url())


    def extra_url(self):
        temp = []
        temp.append(url(r'delete_teacher/(\d+)/(\d+)',self.delete_class_teacher))
        return temp


    list_display = ['school',class_name,get_teachers,'tutor']
    filter_list = ['school','teachers']
    search_fields = ['school']
stark.site.register(models.ClassList,ClassConfig)



class ConsultRecordConfig(DeFaultConfigClass):
    list_display = ['customer','consultant','date','note']
    filter_list = ['customer','consultant']
    search_fields = ['customer']
stark.site.register(models.ConsultRecord,ConsultRecordConfig)



class CourseConfig(DeFaultConfigClass):
    list_display = ['name']
    filter_list = ['name']
    search_fields = ['name']
stark.site.register(models.Course,CourseConfig)


class CourseRecordConfig(DeFaultConfigClass):
    def record(self, obj=None, is_header=False):
        if is_header:
            return '记录'
        return mark_safe('<a href="/stark/crm/studyrecord/?course_record_id=%s">记录</a>' % obj.pk)

    list_display = ['class_obj','day_num','teacher',record]
    filter_list = ['class_obj','teacher']
    search_fields = ['teacher']

    def patch_studyRecord(self,request,queryset):
        '''批量生产学生上课记录'''
        temp = []
        for courseRecord in queryset:
            students = models.Student.objects.filter(class_list=courseRecord.class_obj)
            for student in students:
                obj = models.StudyRecord(student=student,course_record=courseRecord)
                temp.append(obj)
        models.StudyRecord.objects.bulk_create(temp)

    patch_studyRecord.short_description = '批量生成学生上课记录'
    actions = [patch_studyRecord]

stark.site.register(models.CourseRecord,CourseRecordConfig)



class CustomerConfig(DeFaultConfigClass):
    def gender(self,obj=None,is_header=True):
        if is_header:
            return '性别'
        return obj.get_gender_display()
    list_display = ['name','qq',gender]
    filter_list = ['name']
    search_fields = ['name','qq']

    now = datetime.datetime.now()
    day3 = datetime.timedelta(days=3)
    day15 = datetime.timedelta(days=15)
    def publicCustomer(self,request):
        '''公共的客户（三天未跟进或者15天未成交）'''

        customer_list = models.Customer.objects.filter(Q(recv_date__lt=(self.now-self.day15))|Q(last_consult_date__lt=(self.now-self.day3))).exclude(status=1)
        return render(request, 'public_customer.html', locals())

    def qiangDan(self,request,customer_id):
        '''抢单'''
        user_id = 1 # user_id = request.Session.get('user_id')
        ret = models.Customer.objects.filter(pk=customer_id).filter(Q(recv_date__lt=(self.now-self.day15))|Q(last_consult_date__lt=(self.now-self.day3))).update(consultant=user_id,last_consult_date=self.now,recv_date=self.now)
        if not ret:
            return HttpResponse('已被抢了')
        return HttpResponse('抢单成功！')

    def extra_url(self):
        temp = []
        temp.append(url(r'public/',self.publicCustomer))
        temp.append(url(r'qiangdan/(\d+)',self.qiangDan))
        return temp
stark.site.register(models.Customer,CustomerConfig)


class DepartmentConfig(DeFaultConfigClass):
    list_display = ['title','code']
    filter_list = ['title','code']
    search_fields = ['title','code']
stark.site.register(models.Department,DepartmentConfig)


class SchoolConfig(DeFaultConfigClass):
    list_display = ['title']
    filter_list = ['title']
    search_fields = ['title']
stark.site.register(models.School,SchoolConfig)


class StudentConfig(DeFaultConfigClass):
    def showScoreView(self,obj=None,is_header=False):
        if is_header:
            return "成绩展示"
        return mark_safe('<a href="score_view/%s">查看</a>'%obj.pk)

    list_display = ['username','customer',showScoreView]
    filter_list = ['username','customer']
    search_fields = ['username']

    def scoreView(self,request,student_id):
        student = models.Student.objects.filter(pk=student_id).first()
        classes_list = student.class_list.all()
        # print(classes_list)
        student_score_list_all = []
        for classes in classes_list:
            studyRecord_set = models.StudyRecord.objects.filter(student=student,course_record__class_obj=classes)
            student_score_list = []
            score_day_list = []
            for record in studyRecord_set:
                student_score_list.append(record.score)
                score_day_list.append('day%s'%record.course_record.day_num)

            student_score_list_all.append([str(classes),[score_day_list,student_score_list]])
        # [['Python基础(9期)', [['day88', 'day22'], [100, 85]]], ['Python基础(8期)', [['day88', 'day22'], [100, 85]]]]
        # print(student_score_list_all)

        model_list = stark.site.get_model_list(request)
        return render(request, 'student_score.html', locals())

    def extra_url(self):
        temp = []
        temp.append(url(r'score_view/(\d+)/',self.scoreView))
        return temp

stark.site.register(models.Student,StudentConfig)


class StudyRecordConfig(DeFaultConfigClass):
    def homework_note(self,obj=None,is_header=False):
        '''成绩疲于'''
        if is_header:
            return '批语'
        return mark_safe('<span class="homework_note_span" record_id=%s >%s</span>'%(obj.pk,obj.homework_note))

    def changeHomeWorkNote(self,request):
        if request.method == 'POST':
            record_id = request.POST.get('record_id')
            note = request.POST.get('note')
            models.StudyRecord.objects.filter(pk=record_id).update(homework_note = note)
            return JsonResponse({'state':True})

    def changeScore(self, request):
        if request.method == 'POST':
            record_id = request.POST.get('record_id')
            score = request.POST.get('score')
            models.StudyRecord.objects.filter(pk=record_id).update(score=score)
            return JsonResponse({'state': True})

    def extra_url(self):
        temp = []
        temp.append(url(r'change/homework_note/',self.changeHomeWorkNote))
        temp.append(url(r'change/score/',self.changeScore))
        return temp

    def get_score(self,obj=None,is_header=False):
        if is_header:
            return '成绩'
        return mark_safe('<span class="score_span" record_id=%s>%s</span>'%(obj.pk,obj.get_score_display()))

    list_display = ['course_record','student','record',get_score,homework_note]
    filter_list = ['student','record']
    search_fields = ['student']

    def patch_late(self,request,queryset):
        queryset.update(record='late')

    patch_late.short_description = '迟到'
    actions = [patch_late]


stark.site.register(models.StudyRecord,StudyRecordConfig)



class UserInfoConfig(DeFaultConfigClass):
    list_display = ['name','email','depart']
    filter_list = ['name','depart']
    search_fields = ['name','depart']
stark.site.register(models.UserInfo,UserInfoConfig)



stark.site.register(models.CustomerDistrbute)


