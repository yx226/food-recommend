from django.shortcuts import render
from django.shortcuts import HttpResponse
from bson.objectid import ObjectId
# 下载文件要用
from django.http import FileResponse, HttpResponseRedirect
from mainapp import dao as mainapp_dao
from mainapp import recommend as mainapp_RMD
from mainapp import healthdata as mainapp_health
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse

import datetime
import numpy as np
import random

print('===view===')
global RMD
RMD = mainapp_RMD.FoodRMD()

import pymongo
from bson.objectid import ObjectId

# MongoDB 数据库连接配置
try:
    # 连接到本地 MongoDB
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db_dietcat = client['dietcat']  # 使用 dietcat 数据库
    print("MongoDB 连接成功")
except Exception as e:
    print(f"MongoDB 连接失败: {e}")
    # 创建模拟数据库对象以避免错误
    class MockCollection:
        def find(self, *args, **kwargs):
            return []
        def find_one(self, *args, **kwargs):
            return None
        def distinct(self, *args, **kwargs):
            return []
        def count_documents(self, *args, **kwargs):
            return 0
        def update_one(self, *args, **kwargs):
            return type('obj', (object,), {'matched_count': 0})()
        def insert_one(self, *args, **kwargs):
            return type('obj', (object,), {'inserted_id': None})()
        def sort(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def aggregate(self, *args, **kwargs):
            return []
        def delete_one(self, *args, **kwargs):
            return type('obj', (object,), {'deleted_count': 0})()

    class MockDB:
        def __getattr__(self, name):
            return MockCollection()
    
    db_dietcat = MockDB()
# Create your views here.

def food_management(request):
    """菜品管理主页面"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    # 这里可以添加权限检查
    return render(request, 'web/food_management.html')

def update_food_data(request):
    """更新菜品数据"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            shop_name = request.POST.get('shop_name', '').strip()
            food_name = request.POST.get('food_name', '').strip()
            category = request.POST.get('category', '').strip()
            calories = request.POST.get('calories', '').strip()
            protein = request.POST.get('protein', '').strip()
            carbs = request.POST.get('carbs', '').strip()
            fat = request.POST.get('fat', '').strip()
            
            # 构建更新数据
            update_data = {}
            if category:
                update_data['分类'] = category
            if calories:
                update_data['卡路里'] = float(calories)
            if protein:
                update_data['蛋白质'] = float(protein)
            if carbs:
                update_data['碳水化合物'] = float(carbs)
            if fat:
                update_data['脂肪'] = float(fat)
            
            # 执行更新
            if update_data:
                result = mainapp_dao.db_dietcat.ShopFood.update_one(
                    {'商铺名称': shop_name, '菜品': food_name},
                    {'$set': update_data}
                )
                
                if result.matched_count > 0:
                    message = f"成功更新菜品: {food_name}"
                    success = True
                else:
                    message = f"未找到菜品: {food_name}"
                    success = False
            else:
                message = "没有提供更新数据"
                success = False
            
            return render(request, 'web/food_management.html', 
                         {'message': message, 'success': success})
            
        except Exception as e:
            print(f"更新菜品数据出错: {e}")
            return render(request, 'web/food_management.html', 
                         {'message': f'更新失败: {str(e)}', 'success': False})
    
    return redirect('food_management')

def add_food_data(request):
    """添加新菜品"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            food_data = {
                '商铺名称': request.POST.get('shop_name', '').strip(),
                '菜品': request.POST.get('food_name', '').strip(),
                '分类': request.POST.get('category', '其他').strip(),
                '卡路里': float(request.POST.get('calories', 0)),
                '蛋白质': float(request.POST.get('protein', 0)),
                '碳水化合物': float(request.POST.get('carbs', 0)),
                '脂肪': float(request.POST.get('fat', 0)),
                '创建时间': datetime.datetime.now()
            }
            
            # 验证必要字段
            if not food_data['商铺名称'] or not food_data['菜品']:
                return render(request, 'web/food_management.html', 
                            {'message': '商铺名称和菜品名称不能为空', 'success': False})
            
            # 检查是否已存在
            existing = mainapp_dao.db_dietcat.ShopFood.find_one({
                '商铺名称': food_data['商铺名称'],
                '菜品': food_data['菜品']
            })
            
            if existing:
                return render(request, 'web/food_management.html', 
                            {'message': '该菜品已存在', 'success': False})
            
            # 添加新菜品
            result = mainapp_dao.db_dietcat.ShopFood.insert_one(food_data)
            
            if result.inserted_id:
                message = f"成功添加菜品: {food_data['菜品']}"
                success = True
            else:
                message = "添加菜品失败"
                success = False
                
            return render(request, 'web/food_management.html', 
                         {'message': message, 'success': success})
            
        except Exception as e:
            print(f"添加菜品出错: {e}")
            return render(request, 'web/food_management.html', 
                         {'message': f'添加失败: {str(e)}', 'success': False})
    
    return redirect('food_management')

def batch_update_foods(request):
    """批量更新菜品分类"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # 获取所有菜品
            all_foods = list(mainapp_dao.db_dietcat.ShopFood.find())
            updated_count = 0
            
            for food in all_foods:
                food_name = food.get('菜品', '')
                current_category = food.get('分类', '')
                
                # 自动分类逻辑
                auto_category = classify_food_by_name(food_name)
                
                # 如果当前分类为空或与自动分类不同，则更新
                if not current_category or current_category != auto_category:
                    mainapp_dao.db_dietcat.ShopFood.update_one(
                        {'_id': food['_id']},
                        {'$set': {'分类': auto_category}}
                    )
                    updated_count += 1
                    print(f"更新分类: {food_name} -> {auto_category}")
            
            message = f"批量更新完成，共更新 {updated_count} 个菜品的分类"
            return render(request, 'web/food_management.html', 
                         {'message': message, 'success': True})
            
        except Exception as e:
            print(f"批量更新出错: {e}")
            return render(request, 'web/food_management.html', 
                         {'message': f'批量更新失败: {str(e)}', 'success': False})
    
    return redirect('food_management')

def get_food_categories():
    """
    获取菜品分类列表
    """
    categories = {
        '全部': '所有菜品',
        '快餐': '汉堡、炸鸡、披萨等',
        '中餐': '炒菜、米饭、汤类等',
        '面食': '面条、饺子、包子等', 
        '饮品': '奶茶、咖啡、果汁等',
        '小吃': '零食、甜点、烧烤等',
        '早餐': '粥、豆浆、包子等',
        '健康': '沙拉、轻食、低卡等'
    }
    return categories

def classify_food_by_name(food_name):
    """
    根据菜品名称自动分类
    """
    food_name = food_name.lower()
    
    # 快餐类
    if any(keyword in food_name for keyword in ['汉堡', '炸鸡', '披萨', '薯条', '鸡块', '华莱士', '肯德基', '麦当劳']):
        return '快餐'
    
    # 中餐类
    elif any(keyword in food_name for keyword in ['炒饭', '炒面', '米饭', '盖饭', '炒菜', '中餐', '家常菜', '汤']):
        return '中餐'
    
    # 面食类
    elif any(keyword in food_name for keyword in ['面条', '拉面', '刀削面', '饺子', '馄饨', '包子', '馒头', '饼']):
        return '面食'
    
    # 饮品类
    elif any(keyword in food_name for keyword in ['奶茶', '咖啡', '果汁', '饮料', '可乐', '雪碧', '饮品']):
        return '饮品'
    
    # 小吃类
    elif any(keyword in food_name for keyword in ['小吃', '零食', '甜点', '蛋糕', '烧烤', '炸串', '鸡排']):
        return '小吃'
    
    # 早餐类
    elif any(keyword in food_name for keyword in ['粥', '豆浆', '油条', '煎饼', '早餐', '包子', '馒头']):
        return '早餐'
    
    # 健康类
    elif any(keyword in food_name for keyword in ['沙拉', '轻食', '低卡', '健康', '养生', '有机']):
        return '健康'
    
    else:
        return '中餐'  # 默认分类

def get_foods_by_category(category='全部', limit=20):
    """
    根据分类获取菜品
    """
    try:
        if category == '全部':
            foods = list(mainapp_dao.db_dietcat.ShopFood.find().limit(limit))
        else:
            # 先尝试从数据库的分类字段获取
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '分类': category
            }).limit(limit))
            
            # 如果按分类字段找不到，使用名称自动分类
            if not foods:
                all_foods = list(mainapp_dao.db_dietcat.ShopFood.find().limit(100))
                foods = []
                for food in all_foods:
                    food_name = food.get('菜品', '')
                    auto_category = classify_food_by_name(food_name)
                    if auto_category == category:
                        foods.append(food)
                    if len(foods) >= limit:
                        break
        
        return foods
    except Exception as e:
        print(f"获取分类菜品出错: {e}")
        return []

def get_category_page(request, category=None):
    """
    分类页面 - 修复版本
    """
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    print(f"=== 分类页面 ===")
    print(f"URL参数 category: {category}")
    
    # 处理 category 参数
    if category is None:
        # 从 GET 参数获取分类
        category = request.GET.get('category', '全部')
    elif category.isdigit():
        # 如果 category 是数字，说明可能是页码，重置为全部
        print(f"警告: category参数是数字 '{category}'，重置为'全部'")
        category = '全部'
    
    print(f"最终分类: {category}")
    
    # 获取页码（只从GET参数获取）
    page = request.GET.get('page', '1')
    try:
        page = int(page)
    except:
        page = 1
    
    # 每页显示数量
    per_page = 12
    offset = (page - 1) * per_page
    
    try:
        # 获取数据库中的实际分类
        db_categories = mainapp_dao.db_dietcat.ShopFood.distinct('分类')
        print(f"数据库分类: {db_categories}")
        
        # 构建分类字典
        categories_dict = {'全部': '所有菜品'}
        for cat in db_categories:
            if cat == '面食':
                categories_dict[cat] = '面条、饺子、包子等'
            elif cat == '川菜':
                categories_dict[cat] = '麻辣口味菜品'
            elif cat == '小吃':
                categories_dict[cat] = '零食、甜点、烧烤等'
            elif cat == '饮品':
                categories_dict[cat] = '奶茶、咖啡、果汁等'
            elif cat == '西式快餐':
                categories_dict[cat] = '汉堡、炸鸡、披萨等'
            elif cat == '火锅':
                categories_dict[cat] = '麻辣烫、火锅类'
            else:
                categories_dict[cat] = f'{cat}类菜品'
        
        print(f"可用分类: {list(categories_dict.keys())}")
        
        # 获取菜品
        if category == '全部':
            foods = list(mainapp_dao.db_dietcat.ShopFood.find())
            print("获取所有菜品")
        elif category in db_categories:
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({'分类': category}))
            print(f"按分类 '{category}' 查询")
        else:
            print(f"分类 '{category}' 不存在，显示所有菜品")
            foods = list(mainapp_dao.db_dietcat.ShopFood.find())
            category = '全部'
        
        print(f"找到 {len(foods)} 个菜品")
        
        # 分页
        total_foods = len(foods)
        total_pages = max(1, (total_foods + per_page - 1) // per_page)
        page_foods = foods[offset:offset + per_page]
        
        print(f"分页: 第{page}页/共{total_pages}页, 显示{len(page_foods)}个菜品")
        
        # 获取健康提示
        health_tip, health_advice = get_health_recommendation(userId)
        
        return render(request, r'web/category.html',
                      {'foods': page_foods,
                       'current_category': category,
                       'categories': categories_dict,
                       'current_page': page,
                       'total_pages': total_pages,
                       'health_tip': health_tip,
                       'health_advice': health_advice,
                       'total_foods': total_foods})
                       
    except Exception as e:
        print(f"分类页面出错: {e}")
        import traceback
        traceback.print_exc()
        
        # 紧急备用
        return render(request, r'web/category.html',
                      {'foods': [],
                       'current_category': category,
                       'categories': {'全部': '所有菜品'},
                       'current_page': 1,
                       'total_pages': 1,
                       'health_tip': '系统维护中',
                       'health_advice': '正在修复分类功能',
                       'total_foods': 0})

def debug_categories(request):
    """调试分类信息"""
    try:
        # 获取所有分类
        all_categories = mainapp_dao.db_dietcat.ShopFood.distinct('分类')
        
        # 获取所有菜品及其分类
        all_foods = list(mainapp_dao.db_dietcat.ShopFood.find())
        
        result = f"""
        <h1>数据库分类调试信息</h1>
        <h2>所有分类:</h2>
        <ul>
        """
        
        for category in all_categories:
            count = mainapp_dao.db_dietcat.ShopFood.count_documents({'分类': category})
            result += f"<li><strong>{category}</strong>: {count}个菜品</li>"
        
        result += "</ul>"
        
        result += "<h2>所有菜品:</h2><ul>"
        for food in all_foods[:20]:  # 只显示前20个
            result += f"<li>{food.get('商铺名称')} - {food.get('菜品')} - <strong>分类: {food.get('分类')}</strong></li>"
        
        result += "</ul>"
        
        return HttpResponse(result)
        
    except Exception as e:
        return HttpResponse(f"调试出错: {e}")

def debug_database_info(request):
    """
    调试数据库信息
    """
    try:
        db = mainapp_dao.db_dietcat
        collection_names = db.list_collection_names()
        
        print("=== 数据库调试信息 ===")
        print(f"数据库名称: {db.name}")
        print(f"集合列表: {collection_names}")
        
        # 检查 ShopFood 集合
        if 'ShopFood' in collection_names:
            shop_food_count = db.ShopFood.count_documents({})
            print(f"ShopFood 集合文档数量: {shop_food_count}")
            
            # 查看前5个文档的结构
            sample_foods = list(db.ShopFood.find().limit(5))
            print("前5个文档样例:")
            for i, food in enumerate(sample_foods):
                print(f"{i+1}. {food}")
                
        else:
            print("ShopFood 集合不存在")
            
        print("=== 调试结束 ===")
        
        return HttpResponse("检查控制台输出")
        
    except Exception as e:
        print(f"数据库调试出错: {e}")
        return HttpResponse(f"数据库错误: {e}")

def get_path_freq_static_shop(date):
    """
    为每天的每顿饭选择不同的餐厅
    支持动态更新生成不同的推荐
    """
    try:
        # 获取所有商家
        all_shops = mainapp_dao.db_dietcat.ShopFood.distinct('商铺名称')
        
        if not all_shops or len(all_shops) < 4:
            # 返回默认数据或处理商家不足的情况
            return get_fallback_data()
        
        # 使用日期和时间作为种子，确保每次更新都不同
        import time
        random.seed(int(time.time() * 1000))  # 使用当前时间戳
        
        # 随机选择4个不同的餐厅
        selected_shops = random.sample(all_shops, 4)
        
        # 为每顿饭分配餐厅并获取菜品
        breakfast_data = {
            'shop': selected_shops[0],
            'foods': get_foods_for_meal(selected_shops[0], 'breakfast')
        }
        lunch_data = {
            'shop': selected_shops[1],
            'foods': get_foods_for_meal(selected_shops[1], 'lunch')
        }
        dinner_data = {
            'shop': selected_shops[2],
            'foods': get_foods_for_meal(selected_shops[2], 'dinner')
        }
        snack_data = {
            'shop': selected_shops[3],
            'foods': get_foods_for_meal(selected_shops[3], 'snack')
        }
        
        return breakfast_data, lunch_data, dinner_data, snack_data
        
    except Exception as e:
        print(f"分配餐厅餐食出错: {e}")
        return get_fallback_data()

def get_fallback_data():
    """备用数据"""
    empty_data = {'shop': '暂无商家', 'foods': []}
    return empty_data, empty_data, empty_data, empty_data

def get_foods_for_meal(shop_name, meal_type):
    """
    从指定餐厅获取适合某餐段的菜品
    """
    try:
        print(f"正在为 {shop_name} 获取 {meal_type} 菜品")
        
        # 获取该餐厅的所有菜品
        shop_foods = list(mainapp_dao.db_dietcat.ShopFood.find({'商铺名称': shop_name}))
        
        print(f"商家 {shop_name} 共有 {len(shop_foods)} 个菜品")
        
        if not shop_foods:
            return []
        
        # 如果菜品很少，直接返回前几个
        if len(shop_foods) <= 3:
            return shop_foods[:3]
        
        # 根据餐段类型筛选合适的菜品
        suitable_foods = []
        other_foods = []
        
        for food in shop_foods:
            food_name = food.get('菜品', '').lower()
            
            if meal_type == 'breakfast':
                # 早餐适合的菜品
                if any(keyword in food_name for keyword in ['粥', '豆浆', '牛奶', '包子', '馒头', '面包', '油条', '煎饼', '早餐']):
                    suitable_foods.append(food)
                else:
                    other_foods.append(food)
            elif meal_type == 'lunch':
                # 午餐适合的菜品
                if any(keyword in food_name for keyword in ['米饭', '面条', '炒饭', '套餐', '午餐', '便当', '盖饭', '炒面', '饭']):
                    suitable_foods.append(food)
                else:
                    other_foods.append(food)
            elif meal_type == 'dinner':
                # 晚餐适合的菜品
                if any(keyword in food_name for keyword in ['晚餐', '烧烤', '火锅', '正餐', '大餐', '炒菜', '汤', '晚餐']):
                    suitable_foods.append(food)
                else:
                    other_foods.append(food)
            else:  # snack
                # 零食适合的菜品
                if any(keyword in food_name for keyword in ['小吃', '零食', '饮料', '奶茶', '甜点', '蛋糕', '水果', '饮品']):
                    suitable_foods.append(food)
                else:
                    other_foods.append(food)
        
        # 如果找到合适的菜品，返回合适的
        if suitable_foods:
            result = suitable_foods[:3]
        else:
            # 否则返回其他菜品的前几个
            result = other_foods[:3] if other_foods else shop_foods[:3]
        
        print(f"为 {meal_type} 返回 {len(result)} 个菜品")
        return result
        
    except Exception as e:
        print(f"获取{meal_type}菜品出错: {e}")
        return []

# 用户要注册
def register(request):
    if request.method == 'POST':
        # 获取用户名和密码
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        # 检查字段缺失
        if username is None or password is None or \
                username == "" or password == "":
            return render(request, r'web/login.html', {'stat': -1})
        # 检查用户名是否已经注册过了
        if mainapp_dao.docCountInUser({"username": username}) > 0:
            return render(request, r'web/login.html', {'stat': -2})
        # 添加账户名和密码
        mainapp_dao.addDocInUser({"username": username, "password": password})
        # 正确状态返回
        return render(request, r'web/login.html', {'stat': 0})
    # 请求形式是非法的
    return render(request, r'web/login.html', {'stat': -3})


# 去登录界面
def getLoginPage(request):
    return render(request, r'web/login.html')


# 用户要去主页(可能是登录操作,也可能就是单纯的页面切换操作)
def getIndexPage(request):
    mylst = [1 for i in range(12)]  # 方便开发用
    hotFood = mainapp_dao.hotFood()  # 无论如何都要有热门食物
    print(hotFood)
    
    # 看看Session里有没有,有就直接进不做校验
    if request.session.get('_id') is not None and request.session.get('username') is not None:
        favourFood = mainapp_dao.favouriateFood(request.session.get('_id'))
        
        # 🔥 新增：获取健康推荐数据
        health_recommendations = []
        user_health_data = {}
        health_tip = "请完善身体信息获取个性化推荐"
        
        try:
            user_id = request.session.get('_id')
            user = mainapp_dao.firstDocInUser({"_id": ObjectId(user_id)})
            
            # 检查是否有身体数据
            if user.get('weight') and user.get('height'):
                # 计算BMI
                weight_kg = float(user['weight']) / 2
                height_m = float(user['height']) / 100
                bmi = weight_kg / (height_m ** 2)
                
                user_health_data = {
                    'bmi': round(bmi, 1),
                    'body_fat': user.get('body_fat', '--'),
                    'goal': '健康饮食',
                    'daily_calories': '1800-2200'
                }
                
                # 根据BMI生成健康建议
                if bmi < 18.5:
                    health_tip = "💪 增重建议：增加高蛋白食物摄入"
                    health_recommendations = get_health_based_foods('weight_gain')
                elif bmi > 24:
                    health_tip = "🏃 减重建议：选择低卡高蛋白食物"  
                    health_recommendations = get_health_based_foods('weight_loss')
                else:
                    health_tip = "✅ 健康维持：均衡营养搭配"
                    health_recommendations = get_health_based_foods('maintenance')
            else:
                # 如果没有身体数据，使用默认推荐
                health_recommendations = get_default_health_recommendations()
                health_tip = "请完善身体信息获取个性化推荐"
                
        except Exception as e:
            print(f"获取健康推荐数据出错: {e}")
            health_recommendations = get_default_health_recommendations()
        
        return render(request, r'web/index.html', {
            'favourlist': favourFood,
            'hotlist': hotFood,
            'health_recommendations': health_recommendations,  # 🔥 新增
            'user_health_data': user_health_data,              # 🔥 新增
            'health_tip': health_tip                          # 🔥 新增
        })
    
    # 如果是登录操作
    elif request.method == 'POST':
        # 获取用户名和密码
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        # 检查字段缺失
        if username is None or password is None or \
                username == "" or password == "":
            return render(request, r'web/login.html', {'stat': -1})
        # 使用用户名和密码校验身份,并从DB中获取该用户id
        user = mainapp_dao.firstDocInUser({"username": username, "password": password})
        if user is None:
            # 登录失败
            return render(request, r'web/login.html', {'stat': -4})
        # 登录成功,将登录身份存进session里
        userid = user.get('_id').__str__()
        request.session['_id'] = userid  # 转成str
        request.session['username'] = user.get('username')
        favourFood = mainapp_dao.favouriateFood(userid)  # 根据用户名查询最喜爱的食物
        
        # 🔥 新增：登录后也获取健康推荐数据
        health_recommendations = get_default_health_recommendations()
        user_health_data = {}
        health_tip = "请完善身体信息获取个性化推荐"
        
        print("存进了Session里")
        return render(request, r'web/index.html', {
            'favourlist': favourFood,
            'hotlist': hotFood,
            'health_recommendations': health_recommendations,  # 🔥 新增
            'user_health_data': user_health_data,              # 🔥 新增
            'health_tip': health_tip                          # 🔥 新增
        })
    else:
        # 更新:不登录也可以去index页,不登陆不能获取最喜爱的食物
        # 🔥 新增：未登录时也提供默认健康推荐
        health_recommendations = get_default_health_recommendations()
        user_health_data = {}
        health_tip = "登录后获取个性化饮食推荐"
        
        return render(request, r'web/index.html', {
            'favourlist': None,
            'hotlist': hotFood,
            'health_recommendations': health_recommendations,  # 🔥 新增
            'user_health_data': user_health_data,              # 🔥 新增
            'health_tip': health_tip                          # 🔥 新增
        })

def get_health_based_foods(goal_type):
    """根据健康目标获取推荐食物"""
    try:
        if goal_type == 'weight_loss':
            # 减重推荐：低卡路里、高蛋白
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '卡路里': {'$lt': 400},
                '蛋白质': {'$gte': 15}
            }).limit(8))
            
            # 如果没有足够数据，放宽条件
            if len(foods) < 4:
                foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                    '卡路里': {'$lt': 500}
                }).limit(8))
                
        elif goal_type == 'weight_gain':
            # 增重推荐：高蛋白、适中热量
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '蛋白质': {'$gte': 20},
                '卡路里': {'$gte': 400, '$lte': 600}
            }).limit(8))
            
            if len(foods) < 4:
                foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                    '蛋白质': {'$gte': 15}
                }).limit(8))
                
        else:  # maintenance
            # 维持推荐：营养均衡
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '卡路里': {'$gte': 300, '$lte': 550},
                '蛋白质': {'$gte': 12}
            }).limit(8))
            
        # 为每个食物添加健康标签
        for food in foods:
            calories = food.get('卡路里', 0)
            protein = food.get('蛋白质', 0)
            
            if goal_type == 'weight_loss':
                food['health_tag'] = '低卡推荐'
            elif goal_type == 'weight_gain':
                food['health_tag'] = '高蛋白'
            else:
                food['health_tag'] = '均衡营养'
                
            food['health_benefit'] = generate_health_benefit(food, goal_type)
            
        return foods if foods else get_default_health_recommendations()
        
    except Exception as e:
        print(f"获取健康推荐食物出错: {e}")
        return get_default_health_recommendations()

def get_default_health_recommendations():
    """获取默认健康推荐"""
    try:
        # 获取评分高的健康食物
        foods = list(mainapp_dao.db_dietcat.ShopFood.find({
            '评分': {'$gte': 4.0}
        }).limit(8))
        
        for food in foods:
            food['health_tag'] = '热门推荐'
            food['health_benefit'] = '营养均衡的选择'
            
        return foods
    except:
        return []

def generate_health_benefit(food, goal_type):
    """生成健康益处描述"""
    calories = food.get('卡路里', 0)
    protein = food.get('蛋白质', 0)
    carbs = food.get('碳水化合物', 0)
    
    if goal_type == 'weight_loss':
        return f"低卡选择，仅{calories}卡路里，适合控制体重"
    elif goal_type == 'weight_gain':
        return f"高蛋白({protein}g)，提供充足营养"
    else:
        return f"均衡营养：{protein}g蛋白质，{carbs}g碳水"

# 用户要注销登录
def logOut(request):
    request.session.flush()  # 键和值一起清空
    return render(request, r'web/login.html')


# 用户要进入账户资料页面
def getCntMsg(request):
    # 通过检查Session检验是否登录了
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    # 查询用户名和密码
    user = mainapp_dao.firstDocInUser({"_id": ObjectId(userId)})
    username = user.get('username')
    password = user.get('password')
    return render(request, r'web/cntmsg.html', {'userId': userId, 'username': username, 'password': password})


# 用户要进入身体信息页面
def getBdyMsg(request):
    # 通过检查Session检验是否登录了
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    # 获取用户(字典形式)
    user = mainapp_dao.firstDocInUser({"_id": ObjectId(userId)})
    # 计算BMI指数
    weight = None
    height = None
    BMI = ''
    if user.get('weight') is None:
        BMI += '缺少身高!'
    else:
        weight = float(user.get('weight'))
    if user.get('height') is None:
        BMI += '缺少体重!'
    else:
        height = float(user.get('height'))
    if weight is not None and height is not None:
        BMI = (weight / 2) / pow((height / 100), 2)  # 计算BMI的体重使用kg而不是斤
        if BMI < 18.5:
            BMI = str(BMI) + ' (体重过轻)'
        elif BMI < 24:
            BMI = str(BMI) + ' (正常范围)'
        elif BMI < 27:
            BMI = str(BMI) + ' (体重偏重)'
        elif BMI < 30:
            BMI = str(BMI) + ' (轻度肥胖)'
        elif BMI < 35:
            BMI = str(BMI) + ' (中度肥胖)'
        else:
            BMI = str(BMI) + ' (重度肥胖)'
    return render(request, r'web/bdymsg.html', {'user': user, 'bmi': BMI})


# 用户要进入每日打卡页面
def getPunchPage(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    # 获取服务器时间
    userId = request.session.get('_id')
    serverDate = datetime.datetime.now().strftime('%Y-%m-%d')
    return render(request, r'web/punch.html',
                  {'serverDate': serverDate,'year':[datetime.datetime.now().strftime('%Y')],
                   'month': [datetime.datetime.now().strftime('%Y-%m')],
                   'spoleep': mainapp_dao.spoleep(userId, serverDate[0:8]),
                   'walkdata': mainapp_dao.walkreport(userId, serverDate[0:4])})


# ==================== 一日三餐推荐功能 - 单商家版本 ====================

# ==================== 一日三餐推荐功能 - 每日不同商家版本 ====================

# ==================== 一日三餐推荐功能 - 真正每日不同商家版本 ====================

# 添加一个全局变量来记录最近推荐的商家（在实际项目中应该用数据库存储）
RECENT_SHOPS = []

def get_todays_shop():
    """选择今天的推荐商家 - 确保每天不同"""
    try:
        # 获取所有商家
        all_shops = mainapp_dao.db_dietcat.ShopFood.distinct('商铺名称')
        print(f"数据库中共有 {len(all_shops)} 个商家")
        
        if not all_shops:
            return None
        
        # 获取今天的日期作为随机种子
        today = datetime.datetime.now()
        today_str = today.strftime('%Y%m%d')
        random.seed(int(today_str))
        
        # 过滤掉最近7天内推荐过的商家
        available_shops = [shop for shop in all_shops if shop not in RECENT_SHOPS]
        
        # 如果可用商家太少，重置记录（保留最近3个）
        if len(available_shops) < 5:
            if RECENT_SHOPS:
                # 保留最近3个，其他的可以重新推荐
                RECENT_SHOPS = RECENT_SHOPS[-3:]
                available_shops = [shop for shop in all_shops if shop not in RECENT_SHOPS]
            else:
                available_shops = all_shops
        
        # 优先从可用商家中选择
        if available_shops:
            selected_shop = random.choice(available_shops)
        else:
            # 如果没有可用商家，从所有商家中选择
            selected_shop = random.choice(all_shops)
        
        # 记录今天推荐的商家
        if selected_shop not in RECENT_SHOPS:
            RECENT_SHOPS.append(selected_shop)
            # 只保留最近30个记录，防止列表过大
            if len(RECENT_SHOPS) > 30:
                RECENT_SHOPS.pop(0)
        
        print(f"今日推荐商家: {selected_shop}")
        print(f"最近推荐过的商家: {RECENT_SHOPS[-5:]}")  # 显示最近5个
        
        return selected_shop
        
    except Exception as e:
        print(f"选择商家出错: {e}")
        return None

def get_shop_with_sufficient_foods():
    """选择有足够菜品可以分类的商家"""
    try:
        # 获取所有商家及其菜品数量
        pipeline = [
            {'$group': {'_id': '$商铺名称', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 10}}},  # 至少有10个菜品的商家
            {'$sort': {'count': -1}}
        ]
        shops_with_count = list(mainapp_dao.db_dietcat.ShopFood.aggregate(pipeline))
        
        if not shops_with_count:
            # 如果找不到有10个菜品的商家，降低标准
            pipeline = [
                {'$group': {'_id': '$商铺名称', 'count': {'$sum': 1}}},
                {'$match': {'count': {'$gte': 8}}},
                {'$sort': {'count': -1}}
            ]
            shops_with_count = list(mainapp_dao.db_dietcat.ShopFood.aggregate(pipeline))
        
        if shops_with_count:
            # 过滤掉最近推荐过的商家
            available_shops = [shop['_id'] for shop in shops_with_count if shop['_id'] not in RECENT_SHOPS]
            
            if available_shops:
                # 从可用商家中基于日期选择
                today = datetime.datetime.now()
                day_of_year = today.timetuple().tm_yday
                shop_index = day_of_year % len(available_shops)
                selected_shop = available_shops[shop_index]
            else:
                # 如果都推荐过了，选择菜品最多的
                selected_shop = shops_with_count[0]['_id']
            
            print(f"选择有足够菜品的商家: {selected_shop}")
            return selected_shop
        
        return None
        
    except Exception as e:
        print(f"选择有足够菜品商家出错: {e}")
        return None

def filter_shops_by_preference(all_shops, eating_prefer, eating_style):
    """根据用户偏好筛选商家"""
    try:
        preferred_shops = []
        
        # 偏好关键词映射
        prefer_keywords = {
            '辣': ['川菜', '湘菜', '麻辣', '火锅', '香辣', '酸辣'],
            '清淡': ['粥', '汤', '蒸', '煮', '清炒', '白灼', '养生'],
            '甜': ['甜点', '糖水', '甜品', '蛋糕', '奶茶'],
            '咸': ['家常菜', '炒菜', '卤味', '腌制品'],
            '酸': ['酸菜', '醋', '柠檬', '酸辣', '糖醋']
        }
        
        style_keywords = {
            '快餐': ['快餐', '便当', '套餐', '简餐'],
            '正餐': ['餐厅', '饭店', '酒楼', '菜馆'],
            '小吃': ['小吃', '零食', '饮品', '奶茶', '炸鸡'],
            '健康': ['沙拉', '轻食', '健康', '养生', '有机']
        }
        
        for shop in all_shops:
            # 获取商家的部分菜品来判断类型
            shop_foods = list(mainapp_dao.db_dietcat.ShopFood.find(
                {'商铺名称': shop}
            ).limit(10))
            
            if not shop_foods:
                continue
                
            matches_prefer = not eating_prefer  # 如果没有偏好要求，默认匹配
            matches_style = not eating_style    # 如果没有风格要求，默认匹配
            
            # 检查口味偏好
            if eating_prefer and eating_prefer in prefer_keywords:
                for food in shop_foods:
                    food_name = food.get('菜品', '').lower()
                    category = food.get('分类', '').lower()
                    
                    for keyword in prefer_keywords[eating_prefer]:
                        if keyword in food_name or keyword in category:
                            matches_prefer = True
                            break
                    if matches_prefer:
                        break
            
            # 检查饮食风格
            if eating_style and eating_style in style_keywords:
                for food in shop_foods:
                    food_name = food.get('菜品', '').lower()
                    category = food.get('分类', '').lower()
                    
                    for keyword in style_keywords[eating_style]:
                        if keyword in food_name or keyword in category:
                            matches_style = True
                            break
                    if matches_style:
                        break
            
            # 如果匹配偏好，加入推荐列表
            if matches_prefer and matches_style:
                preferred_shops.append(shop)
        
        return preferred_shops if preferred_shops else all_shops
        
    except Exception as e:
        print(f"筛选商家偏好出错: {e}")
        return all_shops

def update_meals_recommendation(request):
    """
    更新餐食推荐 - 换一批餐厅和菜品
    """
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    print("=== 用户请求更新推荐 ===")
    
    # 获取新的餐食分配（每顿饭来自不同餐厅）
    today = datetime.datetime.now()
    
    # 使用当前时间作为额外种子，确保每次更新都不同
    import time
    random.seed(int(time.time()))
    
    breakfast_data, lunch_data, dinner_data, snack_data = get_path_freq_static_shop(today)
    
    # 获取健康提示
    health_tip, health_advice = get_health_recommendation(userId)
    
    # 获取今日日期和星期
    today_date = today.strftime('%Y年%m月%d日')
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekdays[today.weekday()]
    
    return render(request, r'web/meals.html',
                  {'breakfast_data': breakfast_data,
                   'lunch_data': lunch_data,
                   'dinner_data': dinner_data,
                   'snack_data': snack_data,
                   'health_tip': health_tip,
                   'health_advice': health_advice,
                   'today_date': today_date,
                   'weekday': weekday,
                   'show_update_success': True})  # 添加成功提示

def getMealsPage(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    print("=== 每顿饭来自不同餐厅的一日三餐推荐 ===")
    
    # 获取今天的餐食分配（每顿饭来自不同餐厅）
    today = datetime.datetime.now()
    breakfast_data, lunch_data, dinner_data, snack_data = get_path_freq_static_shop(today)
    
    # 添加详细调试信息
    print(f"早餐数据: shop={breakfast_data.get('shop')}, foods数量={len(breakfast_data.get('foods', []))}")
    print(f"午餐数据: shop={lunch_data.get('shop')}, foods数量={len(lunch_data.get('foods', []))}")
    print(f"晚餐数据: shop={dinner_data.get('shop')}, foods数量={len(dinner_data.get('foods', []))}")
    print(f"零食数据: shop={snack_data.get('shop')}, foods数量={len(snack_data.get('foods', []))}")
    
    # 获取健康提示
    health_tip, health_advice = get_health_recommendation(userId)
    
    # 获取今日日期和星期
    today_date = today.strftime('%Y年%m月%d日')
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekdays[today.weekday()]
    
    return render(request, r'web/meals.html',
                  {'breakfast_data': breakfast_data,
                   'lunch_data': lunch_data,
                   'dinner_data': dinner_data,
                   'snack_data': snack_data,
                   'health_tip': health_tip,
                   'health_advice': health_advice,
                   'today_date': today_date,
                   'weekday': weekday})

# 用户要进入设置页面
def getSettingPage(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    return render(request, r'web/setting.html')


# 用户要进入反馈页面
def getPropPage(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    # 从DB中查询
    user = mainapp_dao.firstDocInUser({'_id': ObjectId(userId)})
    return render(request, r'web/prop.html', {'discussion': user.get('discussion', '')})


# 用户要进入食物推荐页面
def getRecommendPage(request, page='1'):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    print("=== 开始分类展示所有菜品 ===")
    print(f"用户ID: {userId}")
    print(f"请求页码: {page}")
    
    try:
        # 获取数据库中所有菜品，按分类组织
        all_foods = list(mainapp_dao.db_dietcat.ShopFood.find())
        print(f"数据库总菜品数量: {len(all_foods)}")
        
        # 按分类分组
        foods_by_category = {}
        for food in all_foods:
            category = food.get('分类', '其他')
            if category not in foods_by_category:
                foods_by_category[category] = []
            foods_by_category[category].append(food)
        
        # 打印分类统计
        print("=== 分类统计 ===")
        for category, foods in foods_by_category.items():
            print(f"{category}: {len(foods)}个菜品")
        
        # 将所有菜品按分类顺序展平（用于分页）
        all_foods_flat = []
        for category in sorted(foods_by_category.keys()):
            all_foods_flat.extend(foods_by_category[category])
        
        recommend = [f"{food['商铺名称']}-{food['菜品']}" for food in all_foods_flat]
        print(f"总推荐菜品数量: {len(recommend)}")
        
        # 基于身体数据的优化推荐（可选，如果不需要可以注释掉）
        # recommend = apply_health_based_recommendation(userId, recommend)
        # print(f"健康优化后推荐数量: {len(recommend)}")
        
    except Exception as e:
        print(f"获取菜品出错: {e}")
        import traceback
        traceback.print_exc()
        # 备用方案
        all_foods = list(mainapp_dao.db_dietcat.ShopFood.find().limit(70))
        recommend = [f"{food['商铺名称']}-{food['菜品']}" for food in all_foods]
        print(f"使用备用方案，菜品数量: {len(recommend)}")
    
    # 去重处理
    unique_recommend = list(set(recommend))
    print(f"去重后推荐数量: {len(unique_recommend)}")
    
    if len(unique_recommend) < len(recommend):
        print("推荐数量不足，补充热门菜品")
        recommend = unique_recommend
        additional_foods = mainapp_dao.FoodNotEnough(len(all_foods) - len(unique_recommend))
        print(f"补充菜品数量: {len(additional_foods)}")
        recommend.extend(additional_foods)
    
    print(f"最终推荐列表长度: {len(recommend)}")
    
    # 分页处理
    start_index = 12 * (int(page) - 1)
    end_index = 12 * (int(page))
    RecommendList = mainapp_dao.RecommendList(recommend)[start_index:end_index]
    
    print(f"分页范围: {start_index} - {end_index}")
    print(f"分页后推荐列表长度: {len(RecommendList)}")
    
    # 获取健康提示
    health_tip, health_advice = get_health_recommendation(userId)
    print(f"健康提示: {health_tip}")
    
    # 计算分页信息
    total_foods = len(recommend)
    total_pages = (total_foods + 11) // 12  # 每页12个，计算总页数
    current_page = int(page)
    
    # 生成分页范围（最多显示5个页码）
    page_range_start = max(1, current_page - 2)
    page_range_end = min(total_pages, current_page + 2)
    page_range = list(range(page_range_start, page_range_end + 1))
    
    print(f"总菜品数: {total_foods}")
    print(f"总页数: {total_pages}")
    print(f"分页范围: {page_range}")
    
    # 获取所有分类用于页面显示
    all_categories = list(foods_by_category.keys()) if 'foods_by_category' in locals() else []
    
    return render(request, r'web/category.html',
        {'foods': RecommendList,                    # 菜品列表
         'page_range': page_range,                  # 分页范围
         'current_page': current_page,              # 当前页码
         'total_pages': total_pages,                # 总页数
         'total_foods': total_foods,                # 总菜品数
         'current_category': '全部菜品',             # 当前分类名称
         'categories': {                            # 分类数据
             '全部': '所有菜品',
             '面食': '面条、饺子、包子等',
             '川菜': '麻辣口味菜品',
             '小吃': '零食、甜点、烧烤等',
             '饮品': '奶茶、咖啡、果汁等',
             '西式快餐': '汉堡、炸鸡、披萨等',
             '火锅': '麻辣烫、火锅类',
             # 根据实际数据库中的分类动态添加
         },
         'health_tip': health_tip,
         'health_advice': health_advice,
         'all_categories': all_categories})         # 所有实际存在的分类

# 用户要进入饮食计划页面
def getPlanPage(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    # 获取用户
    try:
        user = mainapp_dao.firstDocInUser({'_id': ObjectId(userId)})
        user['BMI'] = (int(user['weight']) / 2 / np.square(int(user['height']) / 100))
        serverDate = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 获取健康提示
        health_tip, health_advice = get_health_recommendation(userId)
        
        return render(request, r'web/plan.html',
                      {'user': user, 
                       'sporttime': mainapp_dao.weekspoleep(userId, serverDate),
                       'weekday': mainapp_dao.Week(serverDate),
                       'standard': [mainapp_health.avgstandard(), mainapp_health.avgstandard('优秀', user['sex'])],
                       'status': mainapp_dao.bodystatus(userId),
                       'health_tip': health_tip,
                       'health_advice': health_advice})
    except:
        return render(request, r'web/bdymsg.html', {'user': user, 'bmi': ''})


# 测试下载报表文件
def testDown(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    file = open(r'test/测试报表文件.txt', 'rb')
    response = FileResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="mybb.txt"'
    return response


# 用户要进入某个具体的餐馆页面
def getEateryById(request, id):
    print("获得了餐馆的id", id)
    return render(request, r'web/detail/eatery.html')


# 通过跳转界面添加用户评价
def addEval(request, id):
    print("获得了餐馆的id", id)
    userId = request.session.get('_id')
    RMD.AddEval(userId, mainapp_dao.ID2ShopName(id))
    RMD.AfferADD(userId, mainapp_dao.ID2ShopName(id))
    return HttpResponseRedirect(mainapp_dao.ID2Pic(id))


# 更新身体信息
def updateBodyMsg(request):
    # 检查提交方式
    if request.method != 'POST':
        return render(request, r'web/bdymsg.html')
    # 检查Session
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    # 获取表单提交的内容
    sex = request.POST.get('sex')
    birthday = request.POST.get('birthday')
    height = request.POST.get('height')
    weight = request.POST.get('weight')
    bloodType = request.POST.get('blood-type')
    lungCapacity = request.POST.get('lung-capacity')
    run50 = request.POST.get('run-50')
    visionLeft = request.POST.get('vision-left')
    visionRight = request.POST.get('vision-right')
    sitAndReach = request.POST.get('sit-and-reach')
    standingLongJump = request.POST.get('standing-long-jump')
    ropeSkipping1 = request.POST.get('rope-skipping-1')
    sitUps1 = request.POST.get('sit-ups-1')
    pushUps1 = request.POST.get('push-ups-1')
    eatingPrefer = request.POST.get('eating-prefer')
    eatingStyle = request.POST.get('eating-style')
    sleepTimeAvg = request.POST.get('sleep-time-avg')
    anamnesis = request.POST.get('anamnesis')
    # 测试输出
    print('*' * 20)
    print(sex, birthday, height, weight, bloodType, lungCapacity, run50, visionLeft, visionRight, sitAndReach,
          standingLongJump, ropeSkipping1, sitUps1, pushUps1, eatingPrefer, eatingStyle, sleepTimeAvg, anamnesis)
    print('*' * 20)
    # 更新至数据库
    mainapp_dao.updateOneUser({'_id': ObjectId(userId)},
                          {'sex': sex, 'birthday': birthday, 'height': height, 'weight': weight,
                           'blood_type': bloodType, 'lung_capacity': lungCapacity, 'run_50': run50,
                           'vision_left': visionLeft, 'vision_right': visionRight,
                           'sit_and_reach': sitAndReach, 'standing_long_jump': standingLongJump,
                           'rope_skipping_1': ropeSkipping1, 'sit_ups_1': sitUps1, 'push_ups_1': pushUps1,
                           'eating_prefer': eatingPrefer, 'eating_style': eatingStyle,
                           'sleep_time_avg': sleepTimeAvg, 'anamnesis': anamnesis})
    return getBdyMsg(request)  # 直接调用本页面的函数


#  提交某个用户打卡记录
def subData(request, way):
    serverDate = datetime.datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        # 从Session中获取用户id
        date = request.POST.get('date')
        userId = request.session.get('_id')
        if way == 'spoleep':
            sleep = request.POST.get('sleeptime')
            sport = request.POST.get('sporttime')
            if mainapp_dao.IFdateinData({'用户': userId, '时间': date}) is None:
                mainapp_dao.inputuserdata(userId, date, sleeptime=sleep, sporttime=sport)
            else:
                mainapp_dao.updateuserdata({'用户': userId, '时间': date},
                           {'睡眠时长': sleep, '运动时长': sport})
        elif way == 'walk':
            walkstep = request.POST.get('todaystep')
            if mainapp_dao.IFdateinData({'用户': userId, '时间': date}) is None:
                mainapp_dao.inputuserdata(userId, date, walk=walkstep)
            else:
                mainapp_dao.updateuserdata({'用户': userId, '时间': date},
                           {'步行距离': walkstep})
        elif way == 'job':
            num2job = {'1': '有氧运动', '2': '无氧运动', '3': '应酬', '4': '暴饮暴食', '5': '吸烟', }
            job = []
            num = request.POST.getlist('job')
            for item in num:
                job.append(num2job[item])
            print(job)
            if mainapp_dao.IFdateinData({'用户': userId, '时间': serverDate}) is None:
                mainapp_dao.inputuserdata(userId, serverDate, joblist=job)
            else:
                mainapp_dao.updateuserdata({'用户': userId, '时间': serverDate},
                           {'工作': job})
        elif way == 'food':
            food = [request.POST.get('breakfast'), request.POST.get('lunch'), request.POST.get('dinner')]
            if mainapp_dao.IFdateinData({'用户': userId, '时间': serverDate}) is None:
                mainapp_dao.inputuserdata(userId, serverDate, foodlist=food)
            else:
                mainapp_dao.updateuserdata({'用户': userId, '时间': serverDate},
                           {'食物': food})
    return render(request, r'web/punch.html',
                  {'serverDate': serverDate,'year':[datetime.datetime.now().strftime('%Y')],
                   'month': [datetime.datetime.now().strftime('%Y-%m')],
                   'spoleep': mainapp_dao.spoleep(userId, serverDate[0:8]),
                   'walkdata': mainapp_dao.walkreport(userId, serverDate[0:4])})


# ==================== 新增的健康推荐功能 ====================

def apply_health_based_recommendation(user_id, base_recommendations):
    """基于用户身体数据调整推荐"""
    try:
        user = mainapp_dao.firstDocInUser({"_id": ObjectId(user_id)})
        print(f"健康推荐 - 用户数据: 体重={user.get('weight')}, 身高={user.get('height')}")
        
        # 如果用户没有身体数据，返回原始推荐
        if not user.get('weight') or not user.get('height'):
            print("用户缺少身体数据，使用原始推荐")
            return base_recommendations
        
        # 计算BMI
        weight_kg = float(user['weight']) / 2  # 斤转公斤
        height_m = float(user['height']) / 100  # 厘米转米
        bmi = weight_kg / (height_m ** 2)
        print(f"用户BMI: {bmi:.2f}")
        
        # 获取所有菜品详细信息
        detailed_foods = []
        for food_name in base_recommendations:
            food_detail = get_food_detail(food_name)
            if food_detail:
                detailed_foods.append(food_detail)
        
        # 根据BMI调整推荐策略
        if bmi < 18.5:
            print("用户偏瘦，推荐高蛋白食物")
            optimized_foods = enhance_for_weight_gain(detailed_foods)
        elif bmi > 24:
            print("用户超重，推荐低卡食物")
            optimized_foods = enhance_for_weight_loss(detailed_foods)
        else:
            print("用户体重正常，推荐均衡食物")
            optimized_foods = enhance_for_health_maintenance(detailed_foods)
        
        # 转换回菜品名称列表
        result = [f"{food['商铺名称']}-{food['菜品']}" for food in optimized_foods]
        return result[:70]  # 确保返回70个推荐
            
    except Exception as e:
        print(f"健康推荐出错: {e}")
        return base_recommendations


def get_food_detail(food_name):
    """根据菜品名称获取详细信息 - 增强版本"""
    try:
        print(f"正在查找菜品: {food_name}")
        
        # 处理不同的格式
        if '-' in food_name:
            shop_name, dish_name = food_name.split('-', 1)
            food = mainapp_dao.db_dietcat.ShopFood.find_one({
                '商铺名称': shop_name, 
                '菜品': dish_name
            })
        else:
            # 直接按菜品名查找
            food = mainapp_dao.db_dietcat.ShopFood.find_one({
                '菜品': food_name
            })
        
        if food:
            print(f"找到菜品: {food.get('菜品')}, 卡路里: {food.get('卡路里')}")
        else:
            print(f"未找到菜品: {food_name}")
            
        return food
        
    except Exception as e:
        print(f"获取菜品详情出错 {food_name}: {e}")
        return None


def enhance_for_weight_loss(foods):
    """为减重用户优化推荐 - 低卡路里、高蛋白"""
    try:
        # 过滤低卡路里食物 (< 450卡路里)
        low_calorie = [f for f in foods if f.get('卡路里', 1000) < 450]
        
        if low_calorie:
            # 在高蛋白食物中优先选择
            high_protein = [f for f in low_calorie if f.get('蛋白质', 0) >= 15]
            if high_protein:
                return high_protein
            return low_calorie
        return foods
    except:
        return foods


def enhance_for_weight_gain(foods):
    """为增重用户优化推荐 - 高蛋白、适量热量"""
    try:
        # 选择高蛋白食物 (> 20g蛋白质)
        high_protein = [f for f in foods if f.get('蛋白质', 0) >= 20]
        
        if high_protein:
            # 在适中热量范围内选择 (400-600卡路里)
            moderate_calorie = [f for f in high_protein if 400 <= f.get('卡路里', 0) <= 600]
            if moderate_calorie:
                return moderate_calorie
            return high_protein
        return foods
    except:
        return foods


def enhance_for_health_maintenance(foods):
    """为健康维持用户优化推荐 - 营养均衡"""
    try:
        # 选择营养均衡的食物
        balanced_foods = []
        for food in foods:
            calories = food.get('卡路里', 0)
            protein = food.get('蛋白质', 0)
            carbs = food.get('碳水化合物', 0)
            fat = food.get('脂肪', 0)
            
            # 均衡标准：适中热量，合理营养比例
            if (300 <= calories <= 550 and 
                protein >= 12 and 
                20 <= carbs <= 50 and 
                8 <= fat <= 20):
                balanced_foods.append(food)
        
        return balanced_foods if balanced_foods else foods
    except:
        return foods


def get_health_recommendation(user_id):
    """获取健康建议"""
    try:
        user = mainapp_dao.firstDocInUser({"_id": ObjectId(user_id)})
        
        # 检查是否有身体数据
        if not user.get('weight') or not user.get('height'):
            return "请完善身体信息获取个性化推荐", "前往'身体信息'页面填写身高体重数据"
        
        # 计算BMI
        weight_kg = float(user['weight']) / 2
        height_m = float(user['height']) / 100
        bmi = weight_kg / (height_m ** 2)
        
        # 根据BMI给出建议
        if bmi < 18.5:
            tip = "💪 增重建议"
            advice = f"您的BMI为{bmi:.1f}（偏瘦），建议增加高蛋白食物摄入，如牛肉、鸡蛋、豆制品"
        elif bmi > 24:
            tip = "🏃 减重建议"  
            advice = f"您的BMI为{bmi:.1f}（偏重），推荐低卡高蛋白食物，控制每日热量摄入"
        else:
            tip = "✅ 健康维持"
            advice = f"您的BMI为{bmi:.1f}（正常），继续保持均衡饮食和适量运动"
        
        return tip, advice
        
    except Exception as e:
        print(f"获取健康建议出错: {e}")
        return "个性化推荐", "基于您的身体状况提供定制化外卖推荐"

def update_bdy_msg(request):
    """
    处理更新身体信息的POST请求 - 修复版本
    """
    if request.method == 'POST':
        try:
            # 检查用户是否登录
            user_id = request.session.get('_id')
            if not user_id:
                return redirect('login')
            
            print("=== 开始更新身体信息 ===")
            print(f"用户ID: {user_id}")
            print(f"POST数据: {dict(request.POST)}")
            
            # 获取POST数据中的身体信息字段
            height = request.POST.get('height', '').strip()
            weight = request.POST.get('weight', '').strip()
            age = request.POST.get('age', '').strip()
            gender = request.POST.get('gender', '').strip()
            activity_level = request.POST.get('activity_level', '').strip()
            
            print(f"解析数据 - 身高: {height}, 体重: {weight}, 年龄: {age}, 性别: {gender}, 活动水平: {activity_level}")
            
            # 验证必要数据
            if not height or not weight:
                print("错误: 身高和体重不能为空")
                # 可以在这里添加错误消息传递
                return redirect('bdymsg')
            
            # 转换数据类型
            try:
                height_val = float(height)
                weight_val = float(weight)
                age_val = int(age) if age else 0
            except ValueError as e:
                print(f"数据类型转换错误: {e}")
                return redirect('bdymsg')
            
            # 更新用户信息到数据库 - 使用您现有的 updateOneUser 方法
            update_data = {
                'height': height_val,
                'weight': weight_val
            }
            
            # 可选字段
            if age:
                update_data['age'] = age_val
            if gender:
                update_data['sex'] = gender  # 注意：这里使用 'sex' 与您的数据库字段匹配
            if activity_level:
                update_data['activity_level'] = activity_level
            
            print(f"更新数据: {update_data}")
            
            # 使用您现有的DAO方法更新用户信息
            from bson.objectid import ObjectId
            mainapp_dao.updateOneUser(
                {'_id': ObjectId(user_id)},
                update_data
            )
            
            print("身体信息更新成功！")
            
            # 重定向回身体信息页面
            return redirect('bdymsg')
            
        except Exception as e:
            print(f"更新身体信息错误: {e}")
            import traceback
            traceback.print_exc()
            return redirect('bdymsg')
    else:
        # 如果不是POST请求，重定向到身体信息页面
        return redirect('bdymsg')

# ==================== 评分功能相关视图 ====================

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

@require_POST
@csrf_exempt
def submit_rating(request):
    """处理评分提交"""
    try:
        # 检查用户是否登录
        user_id = request.session.get('_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'})
        
        # 解析JSON数据
        data = json.loads(request.body)
        food_id = data.get('food_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        print(f"收到评分请求 - 用户: {user_id}, 食物ID: {food_id}, 评分: {rating}, 评价: {comment}")
        
        # 验证数据
        if not food_id or not rating:
            return JsonResponse({'success': False, 'message': '缺少必要参数'})
        
        # 获取食物信息
        try:
            food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': ObjectId(food_id)})
            if not food:
                return JsonResponse({'success': False, 'message': '食物不存在'})
        except:
            return JsonResponse({'success': False, 'message': '食物ID格式错误'})
        
        # 创建评分记录
        rating_data = {
            'user_id': user_id,
            'food_id': ObjectId(food_id),
            'rating': int(rating),
            'comment': comment,
            'created_at': datetime.datetime.now(),
            'food_name': food.get('菜品', ''),
            'shop_name': food.get('商铺名称', '')
        }
        
        # 检查是否已经评价过
        existing_rating = mainapp_dao.db_dietcat.FoodRatings.find_one({
            'user_id': user_id,
            'food_id': ObjectId(food_id)
        })
        
        if existing_rating:
            # 更新现有评价
            mainapp_dao.db_dietcat.FoodRatings.update_one(
                {'_id': existing_rating['_id']},
                {'$set': {
                    'rating': int(rating),
                    'comment': comment,
                    'updated_at': datetime.datetime.now()
                }}
            )
            print(f"用户 {user_id} 更新了对 {food.get('菜品')} 的评分")
        else:
            # 插入新评价
            mainapp_dao.db_dietcat.FoodRatings.insert_one(rating_data)
            print(f"用户 {user_id} 对 {food.get('菜品')} 进行了评分")
        
        # 更新食物的平均评分
        update_food_rating_stats(ObjectId(food_id))
        
        return JsonResponse({'success': True, 'message': '评价成功'})
        
    except Exception as e:
        print(f"评分提交出错: {e}")
        return JsonResponse({'success': False, 'message': f'评价失败: {str(e)}'})

def get_food_ratings(request, food_id):
    """获取食物的评价列表"""
    try:
        # 验证食物ID
        try:
            food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': ObjectId(food_id)})
            if not food:
                return JsonResponse({'success': False, 'message': '食物不存在'})
        except:
            return JsonResponse({'success': False, 'message': '食物ID格式错误'})
        
        # 获取评价列表
        ratings = list(mainapp_dao.db_dietcat.FoodRatings.find({
            'food_id': ObjectId(food_id)
        }).sort('created_at', -1).limit(20))
        
        rating_list = []
        for rating in ratings:
            # 获取用户信息（如果有的话）
            user_info = mainapp_dao.firstDocInUser({'_id': ObjectId(rating['user_id'])})
            username = user_info.get('username', '匿名用户') if user_info else '匿名用户'
            
            rating_list.append({
                'user': username,
                'rating': rating['rating'],
                'comment': rating.get('comment', ''),
                'date': rating['created_at'].strftime('%Y-%m-%d %H:%M'),
                'stars': '★' * rating['rating'] + '☆' * (5 - rating['rating'])
            })
        
        return JsonResponse({'success': True, 'ratings': rating_list})
        
    except Exception as e:
        print(f"获取评价列表出错: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

def get_food_rating_stats(request, food_id):
    """获取食物的评分统计"""
    try:
        # 验证食物ID
        try:
            food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': ObjectId(food_id)})
            if not food:
                return JsonResponse({'success': False, 'message': '食物不存在'})
        except:
            return JsonResponse({'success': False, 'message': '食物ID格式错误'})
        
        # 获取评分统计
        pipeline = [
            {'$match': {'food_id': ObjectId(food_id)}},
            {'$group': {
                '_id': '$food_id',
                'average_rating': {'$avg': '$rating'},
                'rating_count': {'$sum': 1},
                'rating_distribution': {
                    '$push': '$rating'
                }
            }}
        ]
        
        stats_result = list(mainapp_dao.db_dietcat.FoodRatings.aggregate(pipeline))
        
        if stats_result:
            stats = stats_result[0]
            average_rating = round(stats['average_rating'], 1)
            rating_count = stats['rating_count']
            
            # 计算评分分布
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for rating in stats['rating_distribution']:
                distribution[rating] += 1
            
            rating_distribution = []
            for i in range(1, 6):
                rating_distribution.append({
                    'rating': i,
                    'count': distribution[i],
                    'percentage': round((distribution[i] / rating_count) * 100, 1) if rating_count > 0 else 0
                })
        else:
            average_rating = 0
            rating_count = 0
            rating_distribution = []
        
        stats_data = {
            'average_rating': average_rating,
            'rating_count': rating_count,
            'rating_distribution': rating_distribution
        }
        
        return JsonResponse({'success': True, 'stats': stats_data})
        
    except Exception as e:
        print(f"获取评分统计出错: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

def update_food_rating_stats(food_id):
    """更新食物的评分统计"""
    try:
        # 计算平均评分
        pipeline = [
            {'$match': {'food_id': food_id}},
            {'$group': {
                '_id': '$food_id',
                'average_rating': {'$avg': '$rating'},
                'rating_count': {'$sum': 1}
            }}
        ]
        
        stats_result = list(mainapp_dao.db_dietcat.FoodRatings.aggregate(pipeline))
        
        if stats_result:
            avg_rating = round(stats_result[0]['average_rating'], 1)
            rating_count = stats_result[0]['rating_count']
        else:
            avg_rating = 0
            rating_count = 0
        
        # 更新食物文档中的评分信息
        mainapp_dao.db_dietcat.ShopFood.update_one(
            {'_id': food_id},
            {'$set': {
                'average_rating': avg_rating,
                'rating_count': rating_count
            }}
        )
        
        print(f"更新食物 {food_id} 的评分统计: 平均分 {avg_rating}, 评价数 {rating_count}")
        
    except Exception as e:
        print(f"更新评分统计出错: {e}")

def rating_success(request):
    """评分成功页面"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    return render(request, 'web/rating_success.html')

def my_ratings(request):
    """我的评分历史页面"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    # 获取用户的评分历史
    user_ratings = list(mainapp_dao.db_dietcat.FoodRatings.find({
        'user_id': user_id
    }).sort('created_at', -1))
    
    # 获取食物详情
    ratings_with_details = []
    for rating in user_ratings:
        food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': rating['food_id']})
        if food:
            rating['food_details'] = food
            ratings_with_details.append(rating)
    
    return render(request, 'web/my_ratings.html', {
        'ratings': ratings_with_details
    })

def get_my_ratings(request):
    """获取当前用户的评分历史（API）"""
    user_id = request.session.get('_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        ratings = list(mainapp_dao.db_dietcat.FoodRatings.find({
            'user_id': user_id
        }).sort('created_at', -1))
        
        rating_list = []
        for rating in ratings:
            food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': rating['food_id']})
            if food:
                rating_list.append({
                    'id': str(rating['_id']),
                    'food_name': food.get('菜品', ''),
                    'shop_name': food.get('商铺名称', ''),
                    'rating': rating['rating'],
                    'comment': rating.get('comment', ''),
                    'date': rating['created_at'].strftime('%Y-%m-%d %H:%M'),
                    'stars': '★' * rating['rating'] + '☆' * (5 - rating['rating'])
                })
        
        return JsonResponse({'success': True, 'ratings': rating_list})
        
    except Exception as e:
        print(f"获取用户评分历史出错: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

def food_detail(request, food_id):
    """食物详情页"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    try:
        # 获取食物详情
        food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': ObjectId(food_id)})
        if not food:
            return render(request, 'web/404.html', {'message': '食物不存在'})
        
        # 获取评价列表
        ratings = list(mainapp_dao.db_dietcat.FoodRatings.find({
            'food_id': ObjectId(food_id)
        }).sort('created_at', -1).limit(20))
        
        # 获取用户是否已经评价过
        user_rating = mainapp_dao.db_dietcat.FoodRatings.find_one({
            'user_id': user_id,
            'food_id': ObjectId(food_id)
        })
        
        # 获取评分统计
        stats_pipeline = [
            {'$match': {'food_id': ObjectId(food_id)}},
            {'$group': {
                '_id': '$food_id',
                'average_rating': {'$avg': '$rating'},
                'rating_count': {'$sum': 1}
            }}
        ]
        
        stats_result = list(mainapp_dao.db_dietcat.FoodRatings.aggregate(stats_pipeline))
        if stats_result:
            average_rating = round(stats_result[0]['average_rating'], 1)
            rating_count = stats_result[0]['rating_count']
        else:
            average_rating = 0
            rating_count = 0
        
        # 准备评价详情
        rating_details = []
        for rating in ratings:
            user_info = mainapp_dao.firstDocInUser({'_id': ObjectId(rating['user_id'])})
            username = user_info.get('username', '匿名用户') if user_info else '匿名用户'
            
            rating_details.append({
                'user': username,
                'rating': rating['rating'],
                'comment': rating.get('comment', ''),
                'date': rating['created_at'].strftime('%Y-%m-%d %H:%M'),
                'stars': '★' * rating['rating'] + '☆' * (5 - rating['rating'])
            })
        
        context = {
            'food': food,
            'ratings': rating_details,
            'user_rating': user_rating,
            'average_rating': average_rating,
            'rating_count': rating_count
        }
        
        return render(request, 'web/food_detail.html', context)
        
    except Exception as e:
        print(f"获取食物详情出错: {e}")
        return render(request, 'web/404.html', {'message': '获取食物详情失败'})

def rating_management(request):
    """评分管理页面（管理员功能）"""
    user_id = request.session.get('_id')
    if not user_id:
        return redirect('login')
    
    # 检查管理员权限
    user = mainapp_dao.firstDocInUser({'_id': ObjectId(user_id)})
    if not user.get('is_staff') and not user.get('is_superuser'):
        return redirect('index')
    
    # 获取所有评分
    ratings = list(mainapp_dao.db_dietcat.FoodRatings.find().sort('created_at', -1))
    
    # 获取评分详情
    ratings_with_details = []
    for rating in ratings:
        food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': rating['food_id']})
        user_info = mainapp_dao.firstDocInUser({'_id': ObjectId(rating['user_id'])})
        
        if food and user_info:
            rating['food_details'] = food
            rating['user_details'] = user_info
            ratings_with_details.append(rating)
    
    return render(request, 'web/rating_management.html', {
        'ratings': ratings_with_details
    })

@require_POST
@csrf_exempt
def delete_rating(request, rating_id):
    """删除评分（管理员功能）"""
    user_id = request.session.get('_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    # 检查管理员权限
    user = mainapp_dao.firstDocInUser({'_id': ObjectId(user_id)})
    if not user.get('is_staff') and not user.get('is_superuser'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    try:
        # 获取评分记录
        rating = mainapp_dao.db_dietcat.FoodRatings.find_one({'_id': ObjectId(rating_id)})
        if not rating:
            return JsonResponse({'success': False, 'message': '评分不存在'})
        
        # 删除评分
        mainapp_dao.db_dietcat.FoodRatings.delete_one({'_id': ObjectId(rating_id)})
        
        # 更新食物评分统计
        update_food_rating_stats(rating['food_id'])
        
        return JsonResponse({'success': True, 'message': '删除成功'})
        
    except Exception as e:
        print(f"删除评分出错: {e}")
        return JsonResponse({'success': False, 'message': str(e)})
# mainapp/dao.py

def hotFood(limit=12):
    """
    获取热门食物
    """
    try:
        print("DAO: 正在查询热门食物...")
        # 尝试从 ShopFood 集合获取数据
        foods = list(db_dietcat.ShopFood.find().limit(limit))
        print(f"DAO: 从数据库获取到 {len(foods)} 个食物")
        
        # 如果数据库为空，返回模拟数据
        if not foods:
            print("DAO: 数据库为空，返回模拟数据")
            return get_sample_hot_foods(limit)
            
        return foods
        
    except Exception as e:
        print(f"DAO: 获取热门食物出错: {e}")
        return get_sample_hot_foods(limit)

def favouriateFood(user_id, limit=12):
    """
    获取用户偏好食物
    """
    try:
        print(f"DAO: 正在查询用户 {user_id} 的偏好食物...")
        
        # 首先尝试获取用户偏好
        user = firstDocInUser({"_id": ObjectId(user_id)})
        eating_prefer = user.get('eating_prefer') if user else None
        
        # 基于用户偏好查询
        query = {}
        if eating_prefer:
            # 根据口味偏好筛选
            prefer_filters = {
                '辣': {'分类': {'$in': ['川菜', '湘菜', '麻辣烫']}},
                '清淡': {'分类': {'$in': ['粥', '汤', '养生']}},
                '甜': {'分类': {'$in': ['甜品', '饮品']}},
                '咸': {'分类': {'$in': ['家常菜', '卤味']}}
            }
            if eating_prefer in prefer_filters:
                query.update(prefer_filters[eating_prefer])
        
        foods = list(db_dietcat.ShopFood.find(query).limit(limit))
        
        if not foods:
            # 如果没有偏好食物，返回高评分食物
            foods = list(db_dietcat.ShopFood.find().sort([("评分", -1)]).limit(limit))
        
        print(f"DAO: 获取到 {len(foods)} 个偏好食物")
        return foods
        
    except Exception as e:
        print(f"DAO: 获取偏好食物出错: {e}")
        return get_sample_favourite_foods(limit)

def get_sample_hot_foods(limit=12):
    """生成模拟的热门食物数据"""
    sample_foods = []
    popular_shops = ["肯德基", "麦当劳", "星巴克", "必胜客", "汉堡王", "真功夫", "永和大王"]
    popular_foods = [
        "香辣鸡腿堡", "巨无霸", "拿铁咖啡", "超级至尊披萨", "皇堡", 
        "排骨饭套餐", "豆浆油条", "炸鸡翅", "薯条", "奶茶", 
        "牛肉面", "沙拉"
    ]
    
    for i in range(min(limit, len(popular_foods))):
        shop = popular_shops[i % len(popular_shops)]
        food_name = popular_foods[i % len(popular_foods)]
        
        sample_foods.append({
            "商铺名称": shop,
            "菜品": f"{food_name}",
            "价格": round(random.uniform(15, 50), 1),
            "原价": round(random.uniform(20, 60), 1),
            "月销量": random.randint(100, 1000),
            "配送时间": f"{random.randint(20, 45)}分钟",
            "起送价": 20,
            "评分": round(random.uniform(3.5, 5.0), 1),
            "分类": random.choice(["快餐", "中餐", "饮品", "西餐"]),
            "商铺链接": f"/static/images/food{i+1}.jpg"
        })
    
    return sample_foods

def get_sample_favourite_foods(limit=12):
    """生成模拟的偏好食物数据"""
    sample_foods = []
    favourite_shops = ["海底捞", "星巴克", "肯德基", "麦当劳", "真功夫", "永和大王"]
    favourite_foods = [
        "火锅套餐", "拿铁咖啡", "香辣鸡腿堡", "巨无霸", "排骨饭", 
        "豆浆油条", "牛肉面", "披萨", "沙拉", "奶茶"
    ]
    
    for i in range(min(limit, len(favourite_foods))):
        shop = favourite_shops[i % len(favourite_shops)]
        food_name = favourite_foods[i % len(favourite_foods)]
        
        sample_foods.append({
            "商铺名称": shop,
            "菜品": f"{food_name}",
            "价格": round(random.uniform(20, 80), 1),
            "原价": round(random.uniform(25, 100), 1),
            "月销量": random.randint(200, 1500),
            "配送时间": f"{random.randint(15, 40)}分钟",
            "起送价": 25,
            "评分": round(random.uniform(4.0, 5.0), 1),
            "分类": random.choice(["火锅", "饮品", "快餐", "中餐", "西餐"]),
            "商铺链接": f"/static/images/fav{i+1}.jpg"
        })
    
    return sample_foods
# mainapp/dao.py

def docCountInUser(query_filter):
    """
    统计用户集合中满足条件的文档数量
    :param query_filter: 查询条件
    :return: 文档数量
    """
    try:
        count = db_dietcat.User.count_documents(query_filter)
        return count
    except Exception as e:
        print(f"统计用户文档数量出错: {e}")
        return 0
# mainapp/dao.py

def addDocInUser(document):
    """
    在用户集合中添加文档
    :param document: 要添加的文档
    :return: 插入结果
    """
    try:
        result = db_dietcat.User.insert_one(document)
        return result
    except Exception as e:
        print(f"添加用户文档出错: {e}")
        return None

def firstDocInUser(query_filter):
    """
    获取用户集合中满足条件的第一个文档
    :param query_filter: 查询条件
    :return: 文档或None
    """
    try:
        document = db_dietcat.User.find_one(query_filter)
        return document
    except Exception as e:
        print(f"获取用户文档出错: {e}")
        return None

def updateOneUser(query_filter, update_data):
    """
    更新用户信息
    """
    try:
        result = db_dietcat.User.update_one(
            query_filter, 
            {'$set': update_data}
        )
        print(f"更新用户信息: 匹配 {result.matched_count} 条, 修改 {result.modified_count} 条")
        return result
    except Exception as e:
        print(f"更新用户信息出错: {e}")
        return None

def hotFood(limit=12):
    """
    获取热门食物
    """
    try:
        # 这里实现获取热门食物的逻辑
        # 例如按评分、销量等排序
        foods = list(db_dietcat.ShopFood.find().sort([("评分", -1), ("月销量", -1)]).limit(limit))
        return foods
    except Exception as e:
        print(f"获取热门食物出错: {e}")
        return []

def favouriateFood(user_id, limit=12):
    """
    获取用户偏好的食物
    """
    try:
        # 这里实现基于用户偏好的食物推荐逻辑
        # 可以根据用户的历史记录、偏好设置等
        foods = list(db_dietcat.ShopFood.find().limit(limit))
        return foods
    except Exception as e:
        print(f"获取偏好食物出错: {e}")
        return []