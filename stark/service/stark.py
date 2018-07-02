# stark 源码
from django.conf.urls import url
from django.shortcuts import render,HttpResponse,redirect
from django.forms import ModelForm
from django.urls import reverse
from django.utils.safestring import mark_safe
from stark.utils.mypage import Pagination
from django.db.models import Q
from django.db.models.fields.related import ManyToManyField,ForeignKey
from django.forms.models import ModelChoiceField


class ShowList:
    def __init__(self,config,data_list,field_list,request):
        self.config = config
        self.data_list = data_list
        self.field_list = field_list
        self.request = request

    def get_header(self):
        # 构建表头
        header_list = []
        for field in self.field_list:
            if callable(field):
                header_list.append(field(self, is_header=True))
            else:
                if field == '__str__':
                    header_list.append(self.config.model._meta.model_name)
                else:
                    ver_name = self.config.model._meta.get_field(field).verbose_name
                    header_list.append(ver_name)
        return header_list

    def get_body(self):
        # 构建表格数据
        new_data_list = []
        for obj in self.data_list:
            temp = []
            for field in self.field_list:

                if callable(field):
                    # 如果是一个函数，则说明是自定义的函数，只需要调用函数即可
                    value = field(self.config, obj,is_header=False)
                else:
                    if field == '__str__':
                        # 如果字段=='__str__'即为未定义list_display属性，使用的是默认的
                        value = getattr(obj, field)
                    else:
                        field_obj = self.config.model._meta.get_field(field)
                        if field_obj.choices:
                            # 如果有字段choices属性
                            # 那么就显示choices属性元组第二个元素，如：choices=(100,A+)，
                            # 通过get_xx_display()获取的就是A+而不是90
                            value = getattr(obj, 'get_%s_display' % field)
                        else:
                            if isinstance(field_obj, ManyToManyField):
                                # 如果是一对多或者多对多
                                # 则求出多的那个对象属于此对象的所有数据
                                data_list = getattr(obj, field).all()
                                l = []
                                for o in data_list:
                                    l.append(str(o))
                                value = ','.join(l)
                            else:
                                # 否则，即为普通字段
                                value = getattr(obj, field)
                                for link in self.config.list_display_link:
                                    # 循环list_display_link，判断如果字段在里面，说明需要有编辑入口的链接
                                    if field == link:
                                        value = mark_safe('<a href="%s">%s</a>' % (self.config.get_change_url(obj), value))
                temp.append(value)
            new_data_list.append(temp)
        return new_data_list

    def get_page_html(self,request,data_list):
        page = request.GET.get('page', 1)
        page_obj = Pagination(page, len(data_list), self.config.get_list_url(), request.GET, per_page_num=5)
        new_data_list = data_list[page_obj.start:page_obj.end]
        page_html = page_obj.page_html()
        return new_data_list,page_html


    def get_action_list(self):
        action_list = self.config.actions
        new_actions_list = []

        def delete_action(self, request, queryset):
            queryset.delete()

        delete_action.short_description = "批量删除"

        new_actions_list.append({
            'name': delete_action.__name__,
            'desc': delete_action.short_description
        })
        for action in action_list:
            new_actions_list.append({
                'name':action.__name__,
                'desc':action.short_description

            })
        return new_actions_list

    def get_filter_list(self):
        import copy

        filter_data_list = []
        filter_field_list = self.config.filter_list   # ['author', 'publish']
        for filter_field in filter_field_list:
            my_request_get = copy.deepcopy(self.request.GET)
            # 获取filter_filter对象
            filter_field_obj = self.config.model._meta.get_field(filter_field)
            # 如果是普通字段
            if not isinstance(filter_field_obj,ForeignKey) and not isinstance(filter_field_obj,ManyToManyField):
                data_list = self.config.model.objects.all().values('pk',filter_field)
            else:
    #             根据filter_field_obj对象获取属于该字段对应的表的所有数据
                data_list = filter_field_obj.rel.to.objects.all()
                # print(data_list)     <QuerySet [<Publish: 北京出版社>, <Publish: 沙河出版社>]>
            temp = []
            if my_request_get.get(filter_field):
                del my_request_get[filter_field]

                temp.append(mark_safe('<a href="?%s">ALL</a>' % my_request_get.urlencode()))
            else:
                temp.append(mark_safe('<a class="active" href="?%s">ALL</a>' % my_request_get.urlencode()))

            for obj in data_list:
                if not isinstance(filter_field_obj, ForeignKey) and not isinstance(filter_field_obj, ManyToManyField):
                    pk = obj['pk']
                    title = obj[filter_field]
                    # 在参数字典里设置键值对
                    my_request_get[filter_field] = title
                else:
                    pk = obj.pk
                    title = str(obj)

                    # 在参数字典里设置键值对
                    my_request_get[filter_field] = pk
                # 判断，目的是为了改变被点击连接颜色
                if  self.request.GET.get(filter_field) == str(pk) or self.request.GET.get(filter_field) == title:
                    temp.append(mark_safe('<a class="active" href="?%s">%s</a>' % (my_request_get.urlencode(), title)))
                else:
                    temp.append(mark_safe('<a href="?%s">%s</a>'%(my_request_get.urlencode(),title)))

            filter_data_list.append({
                'title':filter_field,
                'data':temp
            })
        return filter_data_list




# 一个默认的配置类，
class DeFaultConfigClass:
    list_display = ['__str__']
    list_display_link = []
    search_fields = []
    actions = []
    filter_list = []

    def extra_url(self):
        return []


    def __init__(self,model):
        self.model = model


    # -----------------------------------------------------------------
    # 封装方法，分别获取增删改查的连接（反转）
    def get_change_url(self,obj):
        model_name = self.model._meta.model_name
        app_name = self.model._meta.app_label
        return reverse('%s_%s_change' % (app_name, model_name), args=(obj.pk,))

    def get_delete_url(self,obj):
        model_name = self.model._meta.model_name
        app_name = self.model._meta.app_label
        return reverse('%s_%s_delete' % (app_name, model_name), args=(obj.pk,))

    def get_add_url(self):
        model_name = self.model._meta.model_name
        app_name = self.model._meta.app_label
        return reverse('%s_%s_add' % (app_name, model_name))

    def get_list_url(self):
        model_name = self.model._meta.model_name
        app_name = self.model._meta.app_label
        return reverse('%s_%s' % (app_name, model_name))
    # -----------------------------------------------------------------

    # 定义方法，返回展示页面表头或者编辑删除按钮的连接
    def edit(self, obj=None, is_header=False):
        if is_header:
            return '操作'
        # return mark_safe('<a href="%s">编辑</a>' % self.get_change_url(obj) )
        return mark_safe('<a href="%s"><span class ="glyphicon glyphicon-edit" aria-hidden="true"></span></a>' % self.get_change_url(obj)  )


    def deletes(self, obj=None, is_header=False):
        if is_header:
            return '操作'
        # return mark_safe('<a href="%s">删除</a>' % self.get_delete_url(obj)  )
        return mark_safe('<a href="%s"><span class ="glyphicon glyphicon-trash" aria-hidden="true"></span></a>' % self.get_delete_url(obj)  )





    def check_box(self, obj=None, is_header=False):
        if is_header:
            return mark_safe('<input type="checkbox" id="main_check">')
        return mark_safe('<input type="checkbox" class="fu_check" name="obj_id" value="%s">'%obj.pk)
    # -----------------------------------------------------------------

    # ModelForm实例化方法
    def getForm(self):
        class ModelFormDemo(ModelForm):
            class Meta:
                model=self.model
                fields = '__all__'
        return ModelFormDemo

    # 添加视图
    def add_view(self,request):

        ModelFormDemo = self.getForm()
        form = ModelFormDemo()

        # 判断是否为一对多或者多对多的form字段，以便在前端加入 +
        for form_field in form:
            # print(type(form_field)) # <class 'django.forms.boundfield.BoundField'>
            # print(type(form_field.field)) # <class 'django.forms.models.ModelChoiceField'>

            if isinstance(form_field.field,ModelChoiceField):
                form_field.is_pop = True

                model_name = form_field.field.queryset.model._meta.model_name
                app_name = form_field.field.queryset.model._meta.app_label
                _url = 'stark/%s/%s/add'%(app_name,model_name)

                form_field.url = _url

                form_field.select_box = 'id_'+form_field.name

        if request.method == 'POST':
            select_box = request.GET.get('select_box')
            form = ModelFormDemo(request.POST)
            if form.is_valid():
                obj = form.save()

                if select_box:
                    select_text = str(obj)
                    select_value = obj.pk
                    return render(request,'pop.html',{'select_box':select_box,'select_text':select_text,'select_value':select_value})
                return redirect(self.get_list_url())

        model_list = site.get_model_list(request)
        return render(request,'add_view.html',locals())

    # 修改视图
    def change_view(self,request,id):
        ModelFormDemo = self.getForm()

        obj = self.model.objects.filter(pk=id).first()
        form = ModelFormDemo(instance=obj)

        # 判断是否为一对多或者多对多的form字段，以便在前端加入 +
        for form_field in form:
            # print(type(form_field))  # <class 'django.forms.boundfield.BoundField'>
            # print(type(form_field.field))  # <class 'django.forms.models.ModelChoiceField'>

            if isinstance(form_field.field, ModelChoiceField):
                form_field.is_pop = True

                model_name = form_field.field.queryset.model._meta.model_name
                app_name = form_field.field.queryset.model._meta.app_label
                _url = 'stark/%s/%s/add' % (app_name, model_name)

                form_field.url = _url

                form_field.select_box = 'id_' + form_field.name

        if request.method == 'POST':
            select_box = request.GET.get('select_box')

            form = ModelFormDemo(request.POST, instance=obj)
            if form.is_valid():
                form.save()

                if select_box:
                    select_text = str(obj)
                    select_value = obj.pk
                    return render(request, 'pop.html',
                                  {'select_box': select_box, 'select_text': select_text, 'select_value': select_value})

                return redirect(self.get_list_url())

        model_list = site.get_model_list(request)
        return render(request, 'change_view.html', locals())


    # 删除视图
    def delete_view(self,request,id):
        obj = self.model.objects.filter(pk=id).first()
        obj.delete()
        return redirect(self.get_list_url())

    # 搜索查询
    def get_search_q(self,request):
        kw = request.GET.get('kw')
        if not kw:
            return None
        search_q = Q()
        search_q.connector = 'or'
        for search_field in self.search_fields:
            search_q.children.append((search_field+'__contains',kw))
        return search_q

    def get_filter_q(self,request):
        filter_q = Q()
        for filter_field,filter_field_id in request.GET.items():
            if filter_field != 'page':
                # 排除不在filter_list里的参数，如分页等
                filter_q.children.append((filter_field,filter_field_id))

        return filter_q


    # 查看视图
    def show_data(self,request):

        # action
        if request.method == 'POST':
            action = request.POST.get('action_func')
            obj_id_list = request.POST.getlist('obj_id')

            queryset = self.model.objects.filter(pk__in=obj_id_list)
            if hasattr(self,action):
                action_func = getattr(self,action)
                action_func(request, queryset)

        # 搜索
        search_q = self.get_search_q(request)
        # 过滤
        filter_q = self.get_filter_q(request)

        if search_q:
            data_list = self.model.objects.all().filter(search_q).filter(filter_q)
        else:
            data_list = self.model.objects.all().filter(filter_q)

        field_list = []

        # 拓展表格td,将选择框/编辑删除等加进去
        field_list.append(DeFaultConfigClass.check_box)
        field_list.extend(self.list_display)
        if not self.list_display_link:
            field_list.append(DeFaultConfigClass.edit)
        field_list.append(DeFaultConfigClass.deletes)


        show_list = ShowList(self,data_list,field_list,request)
        header_list = show_list.get_header()
        new_data_list = show_list.get_body()

        add_url = self.get_add_url()

        # 分页
        new_data_list,page_html = show_list.get_page_html(request,new_data_list)

        model_list = site.get_model_list(request)
        return render(request,'show_data.html',locals())


    # 定义一个方法，返回一个（3级）url列表
    # 之所以放在这个类下，是因为starksite类是一个单例模式，放在哎这个类里就可以根据不同的url获取到每一个不同的model对象
    @property
    def get_urls(self):
        model_name = self.model._meta.model_name
        app_name = self.model._meta.app_label
        temp = []



        temp.append(url(r'add$',self.add_view,name='%s_%s_add'%(app_name,model_name)))
        temp.append(url(r'(\d+)/change$',self.change_view,name='%s_%s_change'%(app_name,model_name)))
        temp.append(url(r'(\d+)/delete$',self.delete_view,name='%s_%s_delete'%(app_name,model_name)))
        temp.append(url(r'^$',self.show_data,name='%s_%s'%(app_name,model_name)))

        # 拓展自定已的url
        temp.extend(self.extra_url())

        return temp,None,None


# 定义一个stark服务类，用来生成一个site对象，然后注册
class StarkSite:
    def __init__(self):
        self._registry = {}

    # register方法，用来注册
    def register(self,model,config_class=None):
        if not config_class:
            config_class = DeFaultConfigClass
        self._registry[model] = config_class(model)

    # 获取所有注册过的model以及其对于的list链接
    def get_model_list(self,request):
        model_list = []
        for m in self._registry:
            model_name = m._meta.model_name
            app_name = m._meta.app_label
            href_url = reverse('%s_%s' % (app_name, model_name))

            # 判断当前url和导航链接是否相等或者in（add/edit的情况是in），相等的话说明是选中状态
            if href_url in request.path:
                active = True
            else:
                active = False
            model_list.append(
                {'name': m._meta.model_name, 'href_url': href_url,'active':active}
            )
        return model_list

    # stark主页  http:..127.0.0.1:8000/stark
    def admin(self,request):
        model_list = self.get_model_list(request)
        return render(request,'admin.html',locals())


    # 此方法用来返回一个列表，列表里面是每个2级url
    @property
    def get_urls(self):
        temp = []
        # 注册admin主页url
        temp.append(url(r'^$',self.admin))
        # 循环_registry字典，然后根据对应的键（model）值（config_class）对来生成url
        # url(r'app01/book/',([],None,None))
        for model, config_class_obj in self._registry.items():
            model_name = model._meta.model_name
            app_name = model._meta.app_label
            temp.append(url(r'%s/%s/'%(app_name,model_name),config_class_obj.get_urls))
        return temp

    # urls方法，用来分配url
    @property
    def urls(self):
        return self.get_urls, None, None





# 实例化一个site对象，此对象是单例模式
site = StarkSite()