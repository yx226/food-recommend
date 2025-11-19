from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import RedirectView
from mainapp import views as mainapp_views

def home_redirect(request):
    """
    根路径重定向
    如果用户已登录，跳转到首页；否则跳转到登录页
    """
    if request.session.get('_id'):
        return redirect('index')
    else:
        return redirect('login')

def recommend_redirect(request, page):
    """
    将 /recommend/<page>/ 重定向到 /category/<category>/
    """
    return redirect('category_detail', category=page)

urlpatterns = [
    path('admin/', admin.site.urls),
    # 根路径
    path('', home_redirect, name='home'),
    
    
    # 餐食推荐相关
    path('meals/update/', mainapp_views.update_meals_recommendation, name='update_meals'),
    path('meals/', mainapp_views.getMealsPage, name='meals'),
    
    # 🍱 新增：推荐外卖功能
    path('recommend-food/', mainapp_views.recommend_food, name='recommend_food'),
    path('api/recommend-food/', mainapp_views.recommend_food_api, name='recommend_food_api'),
    
    # 用户认证相关
    path('login/', mainapp_views.getLoginPage, name='login'),
    path('register/', mainapp_views.register, name='register'),
    path('logout/', mainapp_views.logOut, name='logout'),
    
    # 主要页面
    path('index/', mainapp_views.getIndexPage, name='index'),
    path('cntmsg/', mainapp_views.getCntMsg, name='cntmsg'),
    path('bdymsg/', mainapp_views.getBdyMsg, name='bdymsg'),
    path('punch/', mainapp_views.getPunchPage, name='punch'),
    path('setting/', mainapp_views.getSettingPage, name='setting'),
    path('prop/', mainapp_views.getPropPage, name='prop'),
    path('plan/', mainapp_views.getPlanPage, name='plan'),
    
    # 身体信息更新
    path('updatebdymsg/', mainapp_views.updateBodyMsg, name='updatebdymsg'),
    
    # 分类页面
    path('category/', mainapp_views.get_category_page, name='category'),
    path('category/<str:category>/', mainapp_views.get_category_page, name='category_detail'),
    
    # 重定向规则
    path('recommend/', RedirectView.as_view(pattern_name='category', permanent=True)),
    path('recommend/<str:page>/', recommend_redirect, name='recommend_redirect'),
    
    # 功能相关
    path('testdown/', mainapp_views.testDown, name='testdown'),
    path('eatery/<str:id>/', mainapp_views.getEateryById, name='eatery'),
    path('addeval/<str:id>/', mainapp_views.addEval, name='addeval'),
    path('updatebody/', mainapp_views.updateBodyMsg, name='updatebody'),
    path('subdata/<str:way>/', mainapp_views.subData, name='subdata'),
    
    # 分类筛选功能
    path('category-filter/', mainapp_views.get_category_page, name='category_filter'),
    path('category-filter/<str:category>/', mainapp_views.get_category_page, name='category_filter_detail'),
    
    # 调试功能
    path('debug/db/', mainapp_views.debug_database_info, name='debug_db'),
    path('debug/categories/', mainapp_views.debug_categories, name='debug_categories'),
    
    # 菜品管理路由
    path('food-management/', mainapp_views.food_management, name='food_management'),
    path('food-management/update/', mainapp_views.update_food_data, name='update_food'),
    path('food-management/add/', mainapp_views.add_food_data, name='add_food'),
    path('food-management/batch-update/', mainapp_views.batch_update_foods, name='batch_update_foods'),
    
    # 评分功能路由
    path('api/rating/submit/', mainapp_views.submit_rating, name='submit_rating'),
    path('api/rating/<str:food_id>/', mainapp_views.get_food_ratings, name='get_food_ratings'),
    path('api/food/<str:food_id>/rating/', mainapp_views.get_food_rating_stats, name='get_food_rating_stats'),
    path('rating/success/', mainapp_views.rating_success, name='rating_success'),
    
    # 用户评分历史
    path('my-ratings/', mainapp_views.my_ratings, name='my_ratings'),
    path('api/my-ratings/', mainapp_views.get_my_ratings, name='get_my_ratings'),
    
    # 食物详情页
    path('food/<str:food_id>/', mainapp_views.food_detail, name='food_detail'),
    
    # 评分管理（管理员功能）
    path('rating-management/', mainapp_views.rating_management, name='rating_management'),
    path('api/rating/<str:rating_id>/delete/', mainapp_views.delete_rating, name='delete_rating'),
    path('debug/system/', mainapp_views.debug_system_status, name='debug_system'),

    # 🔥 新增AI推荐API路由
    path('api/ai-recommendations/', mainapp_views.get_ai_recommendations_api, name='ai_recommendations'),
    
    # 🔥 新增AI对话功能路由
    path('api/ai-chat/', mainapp_views.ai_chat, name='ai_chat'),
    path('api/conversation-history/', mainapp_views.get_conversation_history, name='conversation_history'),
    path('api/clear-conversation/', mainapp_views.clear_conversation_history, name='clear_conversation'),
]