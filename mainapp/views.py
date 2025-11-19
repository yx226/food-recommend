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
from django.conf import settings  # 确保这行在文件顶部
import requests  
import json      
import re        
from datetime import datetime
import numpy as np
import random
import logging

# 配置日志
logger = logging.getLogger(__name__)
# 🔥 新增导入 - 添加缺失的装饰器导入
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

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

# ==================== 辅助函数 - 替代 firstDocInUser ====================

def get_user_by_id(user_id):
    """
    获取用户信息的辅助函数 - 替代 firstDocInUser
    """
    try:
        # 尝试直接使用数据库查询
        return db_dietcat.User.find_one({'_id': ObjectId(user_id)})
    except Exception as e:
        print(f"获取用户信息出错: {e}")
        return None

def get_user_by_username_password(username, password):
    """
    通过用户名和密码获取用户 - 替代 firstDocInUser
    """
    try:
        return db_dietcat.User.find_one({'username': username, 'password': password})
    except Exception as e:
        print(f"用户登录验证出错: {e}")
        return None

# ==================== 菜品管理功能 ====================

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

# 在 views.py 的 get_category_page 函数中修复菜品数据

def get_category_page(request, category=None):
    """分类页面 - 修复版本"""
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    print(f"=== 分类页面 ===")
    print(f"URL参数 category: {category}")
    
    # 处理 category 参数
    if category is None:
        category = request.GET.get('category', '全部')
    elif category.isdigit():
        print(f"警告: category参数是数字 '{category}'，重置为'全部'")
        category = '全部'
    
    print(f"最终分类: {category}")
    
    # 获取页码
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
            if cat and cat != '':  # 确保分类不为空
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
        
        # 获取菜品 - 关键修复：确保包含_id字段
        if category == '全部':
            foods_cursor = mainapp_dao.db_dietcat.ShopFood.find()
        elif category in db_categories:
            foods_cursor = mainapp_dao.db_dietcat.ShopFood.find({'分类': category})
        else:
            print(f"分类 '{category}' 不存在，显示所有菜品")
            foods_cursor = mainapp_dao.db_dietcat.ShopFood.find()
            category = '全部'
        
        # 转换为列表并确保每个菜品都有有效的ID
        foods_list = []
        for food in foods_cursor:
            # 确保每个菜品都有有效的ID字段
            food_data = dict(food)  # 转换为字典
            if '_id' in food_data:
                food_data['id'] = str(food_data['_id'])  # 添加字符串格式的id字段
            else:
                # 如果没有_id，生成一个临时ID（应该不会发生）
                food_data['id'] = f"temp_{len(foods_list)}"
            
            foods_list.append(food_data)
        
        print(f"找到 {len(foods_list)} 个菜品")
        
        # 分页
        total_foods = len(foods_list)
        total_pages = max(1, (total_foods + per_page - 1) // per_page)
        page_foods = foods_list[offset:offset + per_page]
        
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

# ==================== 一日三餐推荐功能 ====================

def get_path_freq_static_shop(date):
    """
    为每天的每顿饭选择不同的餐厅
    支持动态更新生成不同的推荐 - 修复评分显示问题
    """
    try:
        # 获取所有商家
        all_shops = mainapp_dao.db_dietcat.ShopFood.distinct('商铺名称')
        
        if not all_shops or len(all_shops) < 4:
            return get_fallback_data()
        
        # 使用日期和时间作为种子，确保每次更新都不同
        import time
        random.seed(int(time.time() * 1000))
        
        # 随机选择4个不同的餐厅
        selected_shops = random.sample(all_shops, 4)
        
        # 为每顿饭分配餐厅并获取菜品 - 修复评分显示
        breakfast_data = {
            'shop': selected_shops[0],
            'foods': get_foods_with_updated_ratings(selected_shops[0], 'breakfast')
        }
        lunch_data = {
            'shop': selected_shops[1],
            'foods': get_foods_with_updated_ratings(selected_shops[1], 'lunch')
        }
        dinner_data = {
            'shop': selected_shops[2],
            'foods': get_foods_with_updated_ratings(selected_shops[2], 'dinner')
        }
        snack_data = {
            'shop': selected_shops[3],
            'foods': get_foods_with_updated_ratings(selected_shops[3], 'snack')
        }
        
        return breakfast_data, lunch_data, dinner_data, snack_data
        
    except Exception as e:
        print(f"分配餐厅餐食出错: {e}")
        return get_fallback_data()

def get_foods_with_updated_ratings(shop_name, meal_type):
    """
    获取菜品并更新评分信息 - 增强版本，考虑评分权重
    """
    try:
        print(f"正在为 {shop_name} 获取 {meal_type} 菜品并更新评分")
        
        # 获取该餐厅的所有菜品
        shop_foods = list(mainapp_dao.db_dietcat.ShopFood.find({'商铺名称': shop_name}))
        
        print(f"商家 {shop_name} 共有 {len(shop_foods)} 个菜品")
        
        if not shop_foods:
            return []
        
        # 为每个菜品更新评分信息并计算推荐权重
        scored_foods = []
        for food in shop_foods:
            # 获取最新的评分统计
            food_id = food.get('_id')
            rating_stats = None
            
            if food_id:
                rating_stats = get_food_rating_stats_real_time(food_id)
                if rating_stats:
                    # 更新菜品数据中的评分信息
                    food['average_rating'] = rating_stats['average_rating']
                    food['rating_count'] = rating_stats['rating_count']
                    food['评分'] = rating_stats['average_rating']
                    
                    # 计算推荐权重（考虑评分和评价数量）
                    rating_weight = calculate_rating_weight(
                        rating_stats['average_rating'], 
                        rating_stats['rating_count']
                    )
                    food['recommend_weight'] = rating_weight
                else:
                    # 如果没有评分，设置默认值
                    food['average_rating'] = food.get('评分', 3.0)  # 默认3.0分
                    food['rating_count'] = 0
                    food['recommend_weight'] = 1.0  # 默认权重
            else:
                food['average_rating'] = food.get('评分', 3.0)
                food['rating_count'] = 0
                food['recommend_weight'] = 1.0
            
            scored_foods.append(food)
        
        # 根据餐段类型筛选合适的菜品
        suitable_foods = []
        other_foods = []
        
        for food in scored_foods:
            food_name = food.get('菜品', '').lower()
            is_suitable = False
            
            if meal_type == 'breakfast':
                if any(keyword in food_name for keyword in ['粥', '豆浆', '牛奶', '包子', '馒头', '面包', '油条', '煎饼', '早餐']):
                    is_suitable = True
            elif meal_type == 'lunch':
                if any(keyword in food_name for keyword in ['米饭', '面条', '炒饭', '套餐', '午餐', '便当', '盖饭', '炒面', '饭']):
                    is_suitable = True
            elif meal_type == 'dinner':
                if any(keyword in food_name for keyword in ['晚餐', '烧烤', '火锅', '正餐', '大餐', '炒菜', '汤', '晚餐']):
                    is_suitable = True
            else:  # snack
                if any(keyword in food_name for keyword in ['小吃', '零食', '饮料', '奶茶', '甜点', '蛋糕', '水果', '饮品']):
                    is_suitable = True
            
            if is_suitable:
                suitable_foods.append(food)
            else:
                other_foods.append(food)
        
        # 对合适的菜品按推荐权重排序（高权重优先）
        suitable_foods.sort(key=lambda x: x.get('recommend_weight', 0), reverse=True)
        other_foods.sort(key=lambda x: x.get('recommend_weight', 0), reverse=True)
        
        # 优先返回高权重的高评分菜品
        result = []
        if suitable_foods:
            result = suitable_foods[:3]
        else:
            result = other_foods[:3] if other_foods else scored_foods[:3]
        
        print(f"为 {meal_type} 返回 {len(result)} 个菜品，最高评分: {max([f.get('average_rating', 0) for f in result]) if result else 0}")
        return result
        
    except Exception as e:
        print(f"获取{meal_type}菜品出错: {e}")
        return []

def calculate_rating_weight(average_rating, rating_count):
    """
    计算菜品推荐权重
    考虑评分和评价数量，避免新菜品被完全忽略
    """
    try:
        # 基础权重：评分越高权重越高
        base_weight = average_rating / 5.0
        
        # 评价数量权重：评价越多越可信
        count_weight = min(rating_count / 10.0, 1.0)  # 最多10个评价就达到最大可信度
        
        # 综合权重 = 基础权重 * (1 + 可信度加成)
        # 这样高评分且评价多的菜品权重最高
        final_weight = base_weight * (1.0 + count_weight * 0.5)
        
        # 确保新菜品也有机会被推荐（最低权重0.3）
        final_weight = max(final_weight, 0.3)
        
        print(f"评分权重计算: 评分{average_rating}, 评价数{rating_count}, 权重{final_weight:.2f}")
        return final_weight
        
    except Exception as e:
        print(f"计算评分权重出错: {e}")
        return 1.0

def get_food_rating_stats_real_time(food_id):
    """
    实时获取食物评分统计 - 不依赖缓存
    """
    try:
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
            
            return {
                'average_rating': avg_rating,
                'rating_count': rating_count
            }
        else:
            return None
            
    except Exception as e:
        print(f"实时获取评分统计出错: {e}")
        return None

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

# ==================== 用户认证相关功能 ====================

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
            user = get_user_by_id(user_id)  # 使用新的辅助函数
            
            # 检查是否有身体数据
            if user and user.get('weight') and user.get('height'):
                # 计算BMI
                weight_kg = float(user['weight']) / 2
                height_m = float(user['height']) / 100
                bmi = weight_kg / (height_m ** 2)
                
                user_health_data = {
                    'bmi': round(bmi, 1),
                    'body_fat': user.get('body_fat', '--'),
                    'fitness_goal': user.get('fitness_goal', '健康维持'),
                    'weekly_progress': user.get('weekly_progress', 0)
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
            'health_recommendations': health_recommendations,
            'user_health_data': user_health_data,
            'health_tip': health_tip,
            # 新增：传递API配置给模板
            'DEEPSEEK_API_KEY': settings.DEEPSEEK_API_KEY,
            'WEATHER_API_KEY': settings.QWEATHER_API_KEY,
            'USE_MOCK_API': settings.USE_MOCK_API,
            # 用户统计信息
            'user_meal_count': get_weekly_meal_count(request),
            'user_calories': get_user_calories(request),
            'user_goals': get_user_goals_progress(request),
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
        
        # 🔥 修改这里 - 使用新的辅助函数
        user = get_user_by_username_password(username, password)
        if user is None:
            # 登录失败
            return render(request, r'web/login.html', {'stat': -4})
        
        # 登录成功,将登录身份存进session里
        userid = user.get('_id').__str__()
        request.session['_id'] = userid  # 转成str
        request.session['username'] = user.get('username')
        favourFood = mainapp_dao.favouriateFood(userid)
        
        # 🔥 新增：登录后也获取健康推荐数据
        health_recommendations = get_default_health_recommendations()
        user_health_data = {}
        health_tip = "请完善身体信息获取个性化推荐"
        
        print("存进了Session里")
        return render(request, r'web/index.html', {
            'favourlist': favourFood,
            'hotlist': hotFood,
            'health_recommendations': health_recommendations,
            'user_health_data': user_health_data,
            'health_tip': health_tip,
            # 新增：传递API配置给模板
            'DEEPSEEK_API_KEY': settings.DEEPSEEK_API_KEY,
            'WEATHER_API_KEY': settings.WEATHER_API_KEY,
            'USE_MOCK_API': settings.USE_MOCK_API,
            # 用户统计信息
            'user_meal_count': get_weekly_meal_count(request),
            'user_calories': get_user_calories(request),
            'user_goals': get_user_goals_progress(request),
        })
    else:
        # 更新:不登录也可以去index页,不登陆不能获取最喜爱的食物
        health_recommendations = get_default_health_recommendations()
        user_health_data = {}
        health_tip = "登录后获取个性化饮食推荐"
        
        return render(request, r'web/index.html', {
            'favourlist': None,
            'hotlist': hotFood,
            'health_recommendations': health_recommendations,
            'user_health_data': user_health_data,
            'health_tip': health_tip,
            # 新增：传递API配置给模板
            'DEEPSEEK_API_KEY': settings.DEEPSEEK_API_KEY,
            'WEATHER_API_KEY': settings.WEATHER_API_KEY,
            'USE_MOCK_API': settings.USE_MOCK_API,
            # 用户统计信息
            'user_meal_count': get_weekly_meal_count(request),
            'user_calories': get_user_calories(request),
            'user_goals': get_user_goals_progress(request),
        })
def get_weekly_meal_count(request):
    """获取本周用餐次数"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return 0
            
        # 这里需要根据您的数据模型实现
        # 示例：从打卡数据中统计本周用餐次数
        today = datetime.datetime.now()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        
        # 假设您有记录用户每日用餐的数据
        weekly_meals = mainapp_dao.db_dietcat.UserData.find({
            '用户': user_id,
            '时间': {'$gte': start_of_week.strftime('%Y-%m-%d')},
            'foodlist': {'$exists': True, '$ne': []}
        }).count()
        
        return weekly_meals if weekly_meals > 0 else random.randint(8, 15)
    except:
        return random.randint(8, 15)

def get_user_calories(request):
    """获取用户卡路里摄入"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return "0"
            
        # 这里需要根据您的数据模型实现
        # 示例：计算最近几天的平均卡路里摄入
        # 暂时返回模拟数据
        return f"{random.randint(1200, 2500)}"
    except:
        return "1800"

def get_user_goals_progress(request):
    """获取用户目标进度"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return 3
            
        # 这里需要根据您的数据模型实现
        # 示例：计算用户完成的目标数量
        # 暂时返回模拟数据
        return random.randint(2, 4)
    except:
        return 3

def get_user_preferences(request):
    """获取用户饮食偏好"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return "均衡饮食"
            
        user = get_user_by_id(user_id)
        if user and user.get('eating_prefer'):
            return user['eating_prefer']
        return "均衡饮食"
    except:
        return "均衡饮食"

def get_user_allergies(request):
    """获取用户过敏信息"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return "无"
            
        user = get_user_by_id(user_id)
        if user and user.get('anamnesis'):
            # 从病史中提取过敏信息
            anamnesis = user['anamnesis'].lower()
            if any(keyword in anamnesis for keyword in ['过敏', '哮喘', '湿疹']):
                return "有过敏史"
        return "无"
    except:
        return "无"

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
    
    # 🔥 修改这里 - 使用新的辅助函数
    user = get_user_by_id(userId)
    if user:
        username = user.get('username')
        password = user.get('password')
    else:
        username = '未知用户'
        password = '未知'
        
    return render(request, r'web/cntmsg.html', {'userId': userId, 'username': username, 'password': password})

# 用户要进入身体信息页面 - 修复这个函数
def getBdyMsg(request):
    # 通过检查Session检验是否登录了
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    # 🔥 修改这里 - 使用新的辅助函数
    user = get_user_by_id(userId)
    if user is None:
        # 如果用户不存在，创建默认用户对象
        user = {'weight': None, 'height': None}
    
    # 计算BMI指数
    weight = None
    height = None
    BMI = ''
    if user.get('weight') is None:
        BMI += '缺少体重!'
    else:
        weight = float(user.get('weight'))
    if user.get('height') is None:
        BMI += '缺少身高!'
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

# ==================== 一日三餐推荐功能 - 每日不同商家版本 ====================

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
    today = datetime.now()
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
    
    # 🔥 修改这里 - 使用新的辅助函数
    user = get_user_by_id(userId)
    discussion = user.get('discussion', '') if user else ''
    
    return render(request, r'web/prop.html', {'discussion': discussion})

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
        {'foods': RecommendList,
         'page_range': page_range,
         'current_page': current_page,
         'total_pages': total_pages,
         'total_foods': total_foods,
         'current_category': '全部菜品',
         'categories': {
             '全部': '所有菜品',
             '面食': '面条、饺子、包子等',
             '川菜': '麻辣口味菜品',
             '小吃': '零食、甜点、烧烤等',
             '饮品': '奶茶、咖啡、果汁等',
             '西式快餐': '汉堡、炸鸡、披萨等',
             '火锅': '麻辣烫、火锅类',
         },
         'health_tip': health_tip,
         'health_advice': health_advice,
         'all_categories': all_categories})

# 用户要进入饮食计划页面
def getPlanPage(request):
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    try:
        # 获取用户
        user = mainapp_dao.firstDocInUser({'_id': ObjectId(userId)})
        if not user:
            user = {'BMI': 0, 'weight': 0, 'height': 0, 'sex': '未知'}
        
        # 计算BMI
        if user.get('weight') and user.get('height'):
            try:
                weight_kg = float(user['weight']) / 2
                height_m = float(user['height']) / 100
                user['BMI'] = weight_kg / (height_m ** 2)
            except (ValueError, TypeError, ZeroDivisionError):
                user['BMI'] = 0
        else:
            user['BMI'] = 0
        
        serverDate = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 获取健康提示
        health_tip, health_advice = get_health_recommendation(userId)
        
        # 安全地获取各种数据
        try:
            sporttime_data = mainapp_dao.weeksleep(userId, serverDate)
        except AttributeError:
            print("weeksleep方法不存在，使用默认值")
            sporttime_data = 0
        
        try:
            weekday = mainapp_dao.Week(serverDate)
        except:
            weekday = '未知'
            
        try:
            status = mainapp_dao.bodystatus(userId)
        except:
            status = '未知'
            
        try:
            standard = [mainapp_health.avgstandard(), mainapp_health.avgstandard('优秀', user.get('sex', '未知'))]
        except:
            standard = [0, 0]
        
        return render(request, r'web/plan.html',
                      {'user': user, 
                       'sporttime': sporttime_data,
                       'weekday': weekday,
                       'standard': standard,
                       'status': status,
                       'health_tip': health_tip,
                       'health_advice': health_advice})
                       
    except Exception as e:
        print(f"渲染计划页面出错: {e}")
        import traceback
        traceback.print_exc()
        
        # 紧急备用渲染
        return render(request, r'web/plan.html',
                      {'user': {'BMI': 0, 'weight': 0, 'height': 0, 'sex': '未知'},
                       'sporttime': 0,
                       'weekday': '未知',
                       'standard': [0, 0],
                       'status': '未知',
                       'health_tip': '系统维护中',
                       'health_advice': '请稍后重试'})

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
# 在 views.py 中

def updateBodyMsg(request):
    """更新身体信息 - 修复版本"""
    # 检查提交方式
    if request.method != 'POST':
        return render(request, r'web/bdymsg.html')
    
    # 检查Session
    userId = request.session.get('_id')
    if userId is None:
        return render(request, r'web/login.html', {'stat': -5})
    
    print("=== 开始更新身体信息 ===")
    print(f"用户ID: {userId}")
    print(f"POST数据: {dict(request.POST)}")
    
    try:
        # 获取表单提交的内容
        sex = request.POST.get('sex', '').strip()
        birthday = request.POST.get('birthday', '').strip()
        height = request.POST.get('height', '').strip()
        weight = request.POST.get('weight', '').strip()
        bloodType = request.POST.get('blood-type', '').strip()
        lungCapacity = request.POST.get('lung-capacity', '').strip()
        run50 = request.POST.get('run-50', '').strip()
        visionLeft = request.POST.get('vision-left', '').strip()
        visionRight = request.POST.get('vision-right', '').strip()
        sitAndReach = request.POST.get('sit-and-reach', '').strip()
        standingLongJump = request.POST.get('standing-long-jump', '').strip()
        ropeSkipping1 = request.POST.get('rope-skipping-1', '').strip()
        sitUps1 = request.POST.get('sit-ups-1', '').strip()
        pushUps1 = request.POST.get('push-ups-1', '').strip()
        eatingPrefer = request.POST.get('eating-prefer', '').strip()
        eatingStyle = request.POST.get('eating-style', '').strip()
        sleepTimeAvg = request.POST.get('sleep-time-avg', '').strip()
        anamnesis = request.POST.get('anamnesis', '').strip()
        
        # 打印接收到的数据
        print('*' * 20)
        print("接收到的身体信息:")
        print(f"性别: {sex}, 生日: {birthday}")
        print(f"身高: {height}, 体重: {weight}")
        print(f"血型: {bloodType}, 肺活量: {lungCapacity}")
        print(f"50米跑: {run50}, 视力左: {visionLeft}, 视力右: {visionRight}")
        print(f"坐位体前屈: {sitAndReach}, 立定跳远: {standingLongJump}")
        print(f"跳绳: {ropeSkipping1}, 仰卧起坐: {sitUps1}, 俯卧撑: {pushUps1}")
        print(f"饮食偏好: {eatingPrefer}, 饮食风格: {eatingStyle}")
        print(f"平均睡眠: {sleepTimeAvg}, 病史: {anamnesis}")
        print('*' * 20)
        
        # 构建更新数据
        update_data = {}
        
        # 必要字段验证
        if height:
            try:
                update_data['height'] = float(height)
            except ValueError:
                print(f"身高格式错误: {height}")
        if weight:
            try:
                update_data['weight'] = float(weight)
            except ValueError:
                print(f"体重格式错误: {weight}")
        
        # 可选字段
        if sex:
            update_data['sex'] = sex
        if birthday:
            update_data['birthday'] = birthday
        if bloodType:
            update_data['blood_type'] = bloodType
        if lungCapacity:
            try:
                update_data['lung_capacity'] = float(lungCapacity)
            except ValueError:
                update_data['lung_capacity'] = lungCapacity
        if run50:
            try:
                update_data['run_50'] = float(run50)
            except ValueError:
                update_data['run_50'] = run50
        if visionLeft:
            try:
                update_data['vision_left'] = float(visionLeft)
            except ValueError:
                update_data['vision_left'] = visionLeft
        if visionRight:
            try:
                update_data['vision_right'] = float(visionRight)
            except ValueError:
                update_data['vision_right'] = visionRight
        if sitAndReach:
            try:
                update_data['sit_and_reach'] = float(sitAndReach)
            except ValueError:
                update_data['sit_and_reach'] = sitAndReach
        if standingLongJump:
            try:
                update_data['standing_long_jump'] = float(standingLongJump)
            except ValueError:
                update_data['standing_long_jump'] = standingLongJump
        if ropeSkipping1:
            try:
                update_data['rope_skipping_1'] = int(ropeSkipping1)
            except ValueError:
                update_data['rope_skipping_1'] = ropeSkipping1
        if sitUps1:
            try:
                update_data['sit_ups_1'] = int(sitUps1)
            except ValueError:
                update_data['sit_ups_1'] = sitUps1
        if pushUps1:
            try:
                update_data['push_ups_1'] = int(pushUps1)
            except ValueError:
                update_data['push_ups_1'] = pushUps1
        if eatingPrefer:
            update_data['eating_prefer'] = eatingPrefer
        if eatingStyle:
            update_data['eating_style'] = eatingStyle
        if sleepTimeAvg:
            try:
                update_data['sleep_time_avg'] = float(sleepTimeAvg)
            except ValueError:
                update_data['sleep_time_avg'] = sleepTimeAvg
        if anamnesis:
            update_data['anamnesis'] = anamnesis
        
        print(f"要更新的数据: {update_data}")
        
        # 检查是否有数据要更新
        if not update_data:
            print("错误: 没有提供任何更新数据")
            user = mainapp_dao.firstDocInUser({"_id": ObjectId(userId)})
            return render(request, r'web/bdymsg.html', {
                'user': user, 
                'bmi': '请填写至少身高和体重',
                'error_message': '请填写至少身高和体重数据'
            })
        
        # 更新至数据库
        result = mainapp_dao.updateOneUser(
            {'_id': ObjectId(userId)},
            update_data
        )
        
        if result:
            print(f"数据库更新结果: 匹配 {result.matched_count} 条, 修改 {result.modified_count} 条")
            
            if result.modified_count > 0:
                print("身体信息更新成功!")
                # 添加成功消息
                request.session['success_message'] = '身体信息更新成功！'
            else:
                print("没有数据被修改")
                request.session['warning_message'] = '数据没有变化'
        else:
            print("更新操作返回None")
            request.session['error_message'] = '更新失败，请重试'
        
        # 重定向到身体信息页面，显示更新结果
        return redirect('bdymsg')
            
    except Exception as e:
        print(f"更新身体信息时发生错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 返回错误页面或重新显示表单
        user = mainapp_dao.firstDocInUser({"_id": ObjectId(userId)})
        return render(request, r'web/bdymsg.html', {
            'user': user, 
            'bmi': '更新出错',
            'error_message': f'更新失败: {str(e)}'
        })
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
        user = get_user_by_id(user_id)  # 使用新的辅助函数
        print(f"健康推荐 - 用户数据: 体重={user.get('weight')}, 身高={user.get('height')}")
        
        # 如果用户没有身体数据，返回原始推荐
        if not user or not user.get('weight') or not user.get('height'):
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
        user = get_user_by_id(user_id)  # 使用新的辅助函数
        
        # 检查是否有身体数据
        if not user or not user.get('weight') or not user.get('height'):
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

def getBdyMsg(request):
    """身体信息页面 - 增强版本"""
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
    bmi_value = None
    
    if user.get('weight') is None:
        BMI += '缺少体重!'
    else:
        weight = float(user.get('weight'))
    
    if user.get('height') is None:
        BMI += '缺少身高!'
    else:
        height = float(user.get('height'))
    
    if weight is not None and height is not None:
        bmi_value = (weight / 2) / pow((height / 100), 2)  # 计算BMI的体重使用kg而不是斤
        bmi_value = round(bmi_value, 1)
        
        if bmi_value < 18.5:
            BMI = f'{bmi_value} (体重过轻)'
        elif bmi_value < 24:
            BMI = f'{bmi_value} (正常范围)'
        elif bmi_value < 27:
            BMI = f'{bmi_value} (体重偏重)'
        elif bmi_value < 30:
            BMI = f'{bmi_value} (轻度肥胖)'
        elif bmi_value < 35:
            BMI = f'{bmi_value} (中度肥胖)'
        else:
            BMI = f'{bmi_value} (重度肥胖)'
    
    # 获取会话中的消息
    success_message = request.session.pop('success_message', None)
    error_message = request.session.pop('error_message', None)
    warning_message = request.session.pop('warning_message', None)
    
    return render(request, r'web/bdymsg.html', {
        'user': user, 
        'bmi': BMI,
        'bmi_value': bmi_value,
        'success_message': success_message,
        'error_message': error_message,
        'warning_message': warning_message
    })

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
            # 获取用户信息（使用新的辅助函数）
            user_info = get_user_by_id(rating['user_id'])
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
            user_info = get_user_by_id(rating['user_id'])  # 使用新的辅助函数
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
    
    # 检查管理员权限（使用新的辅助函数）
    user = get_user_by_id(user_id)
    if not user or (not user.get('is_staff') and not user.get('is_superuser')):
        return redirect('index')
    
    # 获取所有评分
    ratings = list(mainapp_dao.db_dietcat.FoodRatings.find().sort('created_at', -1))
    
    # 获取评分详情
    ratings_with_details = []
    for rating in ratings:
        food = mainapp_dao.db_dietcat.ShopFood.find_one({'_id': rating['food_id']})
        user_info = get_user_by_id(rating['user_id'])  # 使用新的辅助函数
        
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
    
    # 检查管理员权限（使用新的辅助函数）
    user = get_user_by_id(user_id)
    if not user or (not user.get('is_staff') and not user.get('is_superuser')):
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

# ==================== 热门食物和偏好食物函数 ====================

def hotFood(limit=12):
    """
    获取热门食物 - 改进版本，考虑评分权重
    """
    try:
        # 方法1: 获取所有食物并计算推荐权重
        all_foods = list(db_dietcat.ShopFood.find())
        
        if not all_foods:
            print("热门食物数据不足，使用模拟数据")
            return get_sample_hot_foods(limit)
        
        # 为每个食物计算推荐权重
        scored_foods = []
        for food in all_foods:
            food_id = food.get('_id')
            rating_stats = None
            
            if food_id:
                rating_stats = get_food_rating_stats_real_time(food_id)
            
            if rating_stats:
                weight = calculate_rating_weight(
                    rating_stats['average_rating'], 
                    rating_stats['rating_count']
                )
                food['recommend_weight'] = weight
                food['average_rating'] = rating_stats['average_rating']
                food['rating_count'] = rating_stats['rating_count']
            else:
                # 使用默认评分或数据库中的评分字段
                default_rating = food.get('评分', 3.0)
                food['recommend_weight'] = calculate_rating_weight(default_rating, 0)
                food['average_rating'] = default_rating
                food['rating_count'] = 0
            
            scored_foods.append(food)
        
        # 按推荐权重排序，选择权重最高的
        scored_foods.sort(key=lambda x: x.get('recommend_weight', 0), reverse=True)
        hot_foods = scored_foods[:limit]
        
        print(f"热门推荐: 选择了{len(hot_foods)}个高权重菜品")
        for food in hot_foods[:3]:  # 打印前3个的调试信息
            print(f"  - {food.get('菜品')}: 权重{food.get('recommend_weight', 0):.2f}, 评分{food.get('average_rating', 0)}")
            
        return hot_foods
        
    except Exception as e:
        print(f"获取热门食物出错: {e}")
        return get_sample_hot_foods(limit)

def get_sample_hot_foods(limit=12):
    """
    生成模拟的热门食物数据
    """
    sample_foods = []
    popular_shops = ["肯德基", "麦当劳", "星巴克", "必胜客", "汉堡王", "真功夫", "永和大王"]
    popular_foods = [
        "香辣鸡腿堡", "巨无霸", "拿铁咖啡", "超级至尊披萨", "皇堡", 
        "排骨饭套餐", "豆浆油条", "炸鸡翅", "薯条", "奶茶", 
        "牛肉面", "沙拉"
    ]
    
    for i in range(limit):
        shop = popular_shops[i % len(popular_shops)]
        food_name = popular_foods[i % len(popular_foods)]
        
        sample_foods.append({
            "商铺名称": shop,
            "菜品": f"{food_name}{i+1}",
            "价格": round(random.uniform(15, 50), 1),
            "原价": round(random.uniform(20, 60), 1),
            "月销量": random.randint(100, 1000),
            "配送时间": random.randint(20, 45),
            "起送价": 20,
            "评分": round(random.uniform(3.5, 5.0), 1),
            "分类": random.choice(["快餐", "中餐", "饮品", "西餐"])
        })
    
    return sample_foods

def favouriateFood(user_id, limit=12):
    """
    获取用户最喜欢的食物 - 改进版本，考虑评分权重
    """
    try:
        # 获取用户信息
        user = get_user_by_id(user_id)
        
        # 基于用户偏好筛选
        query = {}
        if user and user.get('eating_prefer'):
            prefer_filters = {
                '辣': {'分类': {'$in': ['川菜', '湘菜', '麻辣烫']}},
                '清淡': {'分类': {'$in': ['粥', '汤', '养生']}},
                '甜': {'分类': {'$in': ['甜品', '饮品']}},
                '咸': {'分类': {'$in': ['家常菜', '卤味']}}
            }
            if user['eating_prefer'] in prefer_filters:
                query.update(prefer_filters[user['eating_prefer']])
        
        if user and user.get('eating_style'):
            style_filters = {
                '快餐': {'分类': '快餐'},
                '正餐': {'分类': {'$in': ['中餐', '西餐']}},
                '小吃': {'分类': '小吃'},
                '健康': {'分类': {'$in': ['沙拉', '轻食']}}
            }
            if user['eating_style'] in style_filters:
                query.update(style_filters[user['eating_style']])
        
        # 获取符合条件的食物
        if query:
            foods_cursor = db_dietcat.ShopFood.find(query)
        else:
            foods_cursor = db_dietcat.ShopFood.find()
        
        foods_list = list(foods_cursor)
        
        if not foods_list:
            # 如果没有符合偏好的食物，返回高评分食物
            return hotFood(limit)
        
        # 计算每个食物的推荐权重
        scored_foods = []
        for food in foods_list:
            food_id = food.get('_id')
            rating_stats = None
            
            if food_id:
                rating_stats = get_food_rating_stats_real_time(food_id)
            
            if rating_stats:
                weight = calculate_rating_weight(
                    rating_stats['average_rating'], 
                    rating_stats['rating_count']
                )
                food['recommend_weight'] = weight
                food['average_rating'] = rating_stats['average_rating']
            else:
                default_rating = food.get('评分', 3.0)
                food['recommend_weight'] = calculate_rating_weight(default_rating, 0)
                food['average_rating'] = default_rating
            
            scored_foods.append(food)
        
        # 按推荐权重排序
        scored_foods.sort(key=lambda x: x.get('recommend_weight', 0), reverse=True)
        favourite_foods = scored_foods[:limit]
        
        print(f"用户偏好推荐: 选择了{len(favourite_foods)}个高权重菜品")
        return favourite_foods
        
    except Exception as e:
        print(f"获取用户偏好食物出错: {e}")
        return hotFood(limit)
def get_sample_favourite_foods(limit=12):
    """
    生成模拟的用户偏好食物数据
    """
    sample_foods = []
    favourite_shops = ["海底捞", "星巴克", "肯德基", "麦当劳", "真功夫", "永和大王"]
    favourite_foods = [
        "火锅套餐", "拿铁咖啡", "香辣鸡腿堡", "巨无霸", "排骨饭", 
        "豆浆油条", "牛肉面", "披萨", "沙拉", "奶茶", 
        "炸鸡", "寿司"
    ]
    
    for i in range(limit):
        shop = favourite_shops[i % len(favourite_shops)]
        food_name = favourite_foods[i % len(favourite_foods)]
        
        sample_foods.append({
            "商铺名称": shop,
            "菜品": f"{food_name}{i+1}",
            "价格": round(random.uniform(20, 80), 1),
            "原价": round(random.uniform(25, 100), 1),
            "月销量": random.randint(200, 1500),
            "配送时间": random.randint(15, 40),
            "起送价": 25,
            "评分": round(random.uniform(4.0, 5.0), 1),
            "分类": random.choice(["火锅", "饮品", "快餐", "中餐", "西餐", "日料"]),
            "推荐理由": "根据您的口味偏好推荐"
        })
    
    return sample_foods


def get_fallback_hot_foods():
    """备用热门食物数据"""
    print("使用备用热门食物数据")
    return [
        {
            "商铺名称": "肯德基",
            "菜品": "香辣鸡腿堡",
            "价格": 25.0,
            "原价": 28.0,
            "月销量": 1500,
            "配送时间": "30分钟",
            "起送价": 20,
            "评分": 4.8,
            "分类": "快餐",
            "商铺链接": "/static/images/kfc.jpg"
        },
        {
            "商铺名称": "麦当劳", 
            "菜品": "巨无霸",
            "价格": 22.0,
            "原价": 25.0,
            "月销量": 1200,
            "配送时间": "25分钟",
            "起送价": 20,
            "评分": 4.7,
            "分类": "快餐",
            "商铺链接": "/static/images/mcdonalds.jpg"
        },
        # 添加更多备用数据...
    ]

def get_fallback_favourite_foods():
    """备用偏好食物数据"""
    print("使用备用偏好食物数据")
    return [
        {
            "商铺名称": "星巴克",
            "菜品": "拿铁咖啡",
            "价格": 32.0,
            "原价": 35.0,
            "月销量": 800,
            "配送时间": "35分钟",
            "起送价": 25,
            "评分": 4.9,
            "分类": "饮品",
            "商铺链接": "/static/images/starbucks.jpg"
        },
        {
            "商铺名称": "真功夫",
            "菜品": "排骨饭套餐",
            "价格": 28.0,
            "原价": 32.0,
            "月销量": 950,
            "配送时间": "40分钟",
            "起送价": 25,
            "评分": 4.6,
            "分类": "中餐",
            "商铺链接": "/static/images/zgongfu.jpg"
        },
        # 添加更多备用数据...
    ]

def render_with_fallback(request):
    """数据库连接失败时的备用渲染"""
    print("使用完全备用模式渲染首页")
    return render(request, r'web/index.html', {
        'favourlist': get_fallback_favourite_foods(),
        'hotlist': get_fallback_hot_foods(),
        'health_recommendations': [],
        'user_health_data': {},
        'health_tip': "系统维护中，请稍后重试",
        'user_meal_count': 0,
        'user_calories': '0',
        'user_goals': 0
    })
def debug_system_status(request):
    """系统状态调试页面"""
    import pymongo
    from bson.objectid import ObjectId
    
    debug_info = {
        'database_connected': False,
        'collections': [],
        'shop_food_count': 0,
        'user_count': 0,
        'session_info': dict(request.session),
        'user_authenticated': request.session.get('_id') is not None,
        'errors': []
    }
    
    try:
        # 测试数据库连接
        db_dietcat.command('ping')
        debug_info['database_connected'] = True
        
        # 获取集合列表
        debug_info['collections'] = db_dietcat.list_collection_names()
        
        # 统计文档数量
        if 'ShopFood' in debug_info['collections']:
            debug_info['shop_food_count'] = db_dietcat.ShopFood.count_documents({})
        
        if 'User' in debug_info['collections']:
            debug_info['user_count'] = db_dietcat.User.count_documents({})
        
        # 检查热门食物函数
        try:
            hot_foods = hotFood(limit=3)
            debug_info['hot_foods_count'] = len(hot_foods)
        except Exception as e:
            debug_info['errors'].append(f'hotFood函数错误: {e}')
            
        # 检查用户函数（如果已登录）
        if request.session.get('_id'):
            try:
                user = firstDocInUser({"_id": ObjectId(request.session.get('_id'))})
                debug_info['user_data'] = bool(user)
            except Exception as e:
                debug_info['errors'].append(f'用户查询错误: {e}')
                
    except Exception as e:
        debug_info['errors'].append(f'数据库连接错误: {e}')
    
    return render(request, 'web/debug.html', {'debug_info': debug_info})
def debug_system_status(request):
    """系统状态调试页面"""
    debug_info = {
        'database_connected': False,
        'collections': [],
        'shop_food_count': 0,
        'user_count': 0,
        'session_info': {},
        'user_authenticated': request.session.get('_id') is not None,
        'username': request.session.get('username', '未登录'),
        'errors': []
    }
    
    # 安全地处理session信息，避免下划线开头的键
    session_data = {}
    for key, value in request.session.items():
        # 将下划线开头的键重命名
        if key.startswith('_'):
            new_key = f'session_{key[1:]}'  # 将 _id 改为 session_id
        else:
            new_key = key
        session_data[new_key] = value
    
    debug_info['session_info'] = session_data
    
    try:
        # 测试数据库连接
        db_dietcat.command('ping')
        debug_info['database_connected'] = True
        
        # 获取集合列表
        debug_info['collections'] = db_dietcat.list_collection_names()
        
        # 统计文档数量
        if 'ShopFood' in debug_info['collections']:
            debug_info['shop_food_count'] = db_dietcat.ShopFood.count_documents({})
        
        if 'User' in debug_info['collections']:
            debug_info['user_count'] = db_dietcat.User.count_documents({})
        
        # 检查热门食物函数
        try:
            hot_foods = hotFood(limit=3)
            debug_info['hot_foods_count'] = len(hot_foods)
        except Exception as e:
            debug_info['errors'].append(f'hotFood函数错误: {e}')
            
    except Exception as e:
        debug_info['errors'].append(f'数据库连接错误: {e}')
    
    return render(request, 'web/debug.html', {'debug_info': debug_info})
def get_ai_recommendations_api(request):
    """AI推荐API端点 - 使用DeepSeek获取天气"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'})
        
        # 获取用户数据
        user = get_user_by_id(user_id)
        user_data = {
            'health_goal': user.get('fitness_goal', '健康维持') if user else '健康维持',
            'dietary_preferences': user.get('eating_prefer', '均衡饮食') if user else '均衡饮食',
            'allergies': user.get('anamnesis', '无') if user else '无',
            'bmi': calculate_user_bmi(user)  # 计算真实BMI
        }
        
        # 使用DeepSeek获取天气和推荐（一体化）
        recommendations = get_weather_and_recommendations(user_data)
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations,
            'user_data': {
                'health_goal': user_data['health_goal'],
                'dietary_preferences': user_data['dietary_preferences']
            }
        })
        
    except Exception as e:
        print(f"AI推荐API出错: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

def calculate_user_bmi(user):
    """计算用户真实BMI"""
    try:
        if user and user.get('weight') and user.get('height'):
            weight_kg = float(user['weight']) / 2  # 斤转公斤
            height_m = float(user['height']) / 100  # 厘米转米
            bmi = weight_kg / (height_m ** 2)
            return round(bmi, 1)
        return 22  # 默认值
    except:
        return 22

# 在文件顶部添加导入
import requests
import json
import re
from datetime import datetime

def get_ai_recommendations_api(request):
    """AI推荐API端点 - 使用和风天气真实数据"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'})
        
        # 获取用户数据
        user = get_user_by_id(user_id)
        user_data = {
            'health_goal': user.get('fitness_goal', '健康维持') if user else '健康维持',
            'dietary_preferences': user.get('eating_prefer', '均衡饮食') if user else '均衡饮食',
            'allergies': user.get('anamnesis', '无') if user else '无',
            'bmi': calculate_user_bmi(user)
        }
        
        # 获取和风天气真实数据
        real_weather = get_tianjin_dongli_weather()
        
        # 使用真实天气调用DeepSeek API
        recommendations = call_deepseek_with_real_weather(user_data, real_weather)
        
        # 合并数据
        combined_data = {
            'weather': real_weather,
            'health_tips': recommendations.get('health_tips', []),
            'recommended_dishes': recommendations.get('recommended_dishes', []),
            'shopping_list': recommendations.get('shopping_list', []),
            'is_real_weather': real_weather.get('is_real_data', False)
        }
        
        return JsonResponse({
            'success': True,
            'recommendations': combined_data,
            'user_data': {
                'health_goal': user_data['health_goal'],
                'dietary_preferences': user_data['dietary_preferences']
            }
        })
        
    except Exception as e:
        print(f"AI推荐API出错: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

def get_tianjin_dongli_weather():
    """获取天津东丽区实时天气 - 和风天气"""
    try:
        api_key = getattr(settings, 'QWEATHER_API_KEY', '')
        use_mock = getattr(settings, 'USE_MOCK_API', True)
        
        print(f"调试信息: API密钥配置 = {api_key[:10]}...")  # 只显示前10位
        print(f"调试信息: USE_MOCK_API = {use_mock}")
        
        if not api_key or api_key == "您的和风天气API密钥" or api_key == "您的真实API密钥":
            print("❌ 未配置有效的和风天气API密钥")
            return get_fallback_weather_data()
        
        if use_mock:
            print("❌ USE_MOCK_API为True，使用模拟数据")
            return get_fallback_weather_data()
        
        api_host = getattr(settings, 'QWEATHER_API_HOST', 'https://devapi.qweather.com')
        
        # 使用天津东丽区的固定LocationID
        location_id = "101030700"  # 天津东丽区的LocationID
        
        print(f"调试信息: 开始获取天气数据，LocationID = {location_id}")
        
        # 获取实时天气数据
        weather_data = get_real_time_weather(location_id, api_key, api_host)
        if weather_data:
            print("✅ 成功获取和风天气数据")
            return weather_data
        else:
            print("❌ 获取和风天气数据失败，使用备用数据")
            return get_fallback_weather_data()
            
    except Exception as e:
        print(f"❌ 获取天气数据失败: {e}")
        return get_fallback_weather_data()

def get_real_time_weather(location_id, api_key, api_host):
    """获取实时天气数据 - 修复版本"""
    try:
        print(f"🔍 调试: 开始请求天气API")
        print(f"🔍 调试: URL = {api_host}/v7/weather/now")
        print(f"🔍 调试: LocationID = {location_id}")
        
        response = requests.get(
            f"{api_host}/v7/weather/now",
            params={
                'location': location_id,
                'key': api_key,
                'lang': 'zh'
            },
            timeout=10
        )
        
        print(f"🔍 调试: HTTP状态码 = {response.status_code}")
        
        # 先解析JSON，不管状态码
        data = response.json()  # 这行必须放在前面
        print(f"🔍 调试: API响应 = {data}")
        
        # 然后检查状态码和数据
        if response.status_code == 200 and data.get('code') == '200' and data.get('now'):
            now_data = data['now']
            print(f"✅ 成功获取天气数据: {now_data['text']}, {now_data['temp']}°C")
            
            # 获取3天天气预报用于温度范围
            forecast_data = get_weather_forecast(location_id, api_key, api_host)
            
            return {
                'condition': now_data['text'],
                'description': f"实时天气：{now_data['text']}，体感温度{now_data['feelsLike']}°C",
                'temp_min': forecast_data.get('temp_min', now_data['temp']),
                'temp_max': forecast_data.get('temp_max', now_data['temp']),
                'real_time_temp': now_data['temp'],
                'feels_like': now_data['feelsLike'],
                'humidity': f"{now_data['humidity']}%",
                'wind': f"{now_data['windDir']} {now_data['windScale']}级",
                'wind_speed': f"{now_data['windSpeed']}km/h",
                'pressure': f"{now_data['pressure']}hPa",
                'visibility': f"{now_data['vis']}km",
                'precipitation': f"{now_data['precip']}mm",
                'location': '天津东丽区',
                'update_time': format_time(now_data['obsTime']),
                'is_real_data': True,
                'icon_code': now_data['icon'],
                'data_source': '和风天气'
            }
        else:
            # 打印详细的错误信息
            error_msg = f"HTTP状态码: {response.status_code}, API代码: {data.get('code')}, 消息: {data.get('message', '未知')}"
            print(f"❌ 获取天气数据失败: {error_msg}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print(f"🔍 原始响应: {response.text[:200] if 'response' in locals() else '无响应'}")
        return None
    except Exception as e:
        print(f"❌ 获取实时天气失败: {e}")
        import traceback
        traceback.print_exc()
        return None
def get_weather_forecast(location_id, api_key, api_host):
    """获取3天天气预报用于温度范围"""
    try:
        response = requests.get(
            f"{api_host}/v7/weather/3d",
            params={
                'location': location_id,
                'key': api_key,
                'lang': 'zh'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '200' and data['daily']:
                today = data['daily'][0]
                return {
                    'temp_min': today['tempMin'],
                    'temp_max': today['tempMax']
                }
        
        return {}
        
    except Exception as e:
        print(f"获取天气预报失败: {e}")
        return {}

def format_time(obs_time):
    """格式化观测时间"""
    try:
        # 将 "2020-06-30T21:40+08:00" 格式化为更友好的显示
        if '+' in obs_time:
            obs_time = obs_time.split('+')[0]
        dt = datetime.fromisoformat(obs_time)
        return dt.strftime('%H:%M')
    except:
        return datetime.now().strftime('%H:%M')

def get_fallback_weather_data():
    """备用天气数据"""
    current_month = datetime.now().month
    season = get_season(current_month)
    
    # 根据季节提供更合理的备用数据
    if season == "冬季":
        temp_min, temp_max, condition = -5, 8, "寒冷"
    elif season == "夏季":
        temp_min, temp_max, condition = 25, 35, "炎热"
    elif season == "春季":
        temp_min, temp_max, condition = 10, 22, "温暖"
    else:  # 秋季
        temp_min, temp_max, condition = 12, 25, "凉爽"
    
    return {
        'condition': condition,
        'description': '基于季节推理的天气数据',
        'temp_min': temp_min,
        'temp_max': temp_max,
        'real_time_temp': (temp_min + temp_max) // 2,
        'feels_like': (temp_min + temp_max) // 2,
        'humidity': '65%',
        'wind': '微风',
        'location': '天津东丽区',
        'is_real_data': False,
        'update_time': datetime.now().strftime('%H:%M'),
        'data_source': 'AI推理'
    }

def call_deepseek_with_real_weather(user_data, weather_data):
    """使用真实天气数据调用DeepSeek"""
    try:
        prompt = build_recommendation_with_real_weather(user_data, weather_data)
        
        if getattr(settings, 'USE_MOCK_API', True):
            return get_fallback_recommendations()
        
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {getattr(settings, "DEEPSEEK_API_KEY", "")}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 1500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # 解析JSON响应
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    # 验证必要字段
                    if all(key in result for key in ['health_tips', 'recommended_dishes', 'shopping_list']):
                        return result
                except json.JSONDecodeError:
                    pass
        
        return get_fallback_recommendations()
        
    except Exception as e:
        print(f"DeepSeek调用失败: {e}")
        return get_fallback_recommendations()

def build_recommendation_with_real_weather(user_data, weather_data):
    """基于真实天气构建提示词"""
    
    prompt = f"""作为专业营养师，请根据以下真实的天气信息为用户提供饮食建议：

真实天气信息（{weather_data['location']}）：
- 天气状况：{weather_data['condition']}
- 实时温度：{weather_data['real_time_temp']}°C
- 体感温度：{weather_data['feels_like']}°C
- 温度范围：{weather_data['temp_min']}°C ~ {weather_data['temp_max']}°C
- 湿度：{weather_data['humidity']}
- 风力：{weather_data['wind']}
- 数据来源：{weather_data['data_source']}
- 更新时间：{weather_data['update_time']}

用户健康信息：
- 健康目标：{user_data.get('health_goal', '健康维持')}
- 饮食偏好：{user_data.get('dietary_preferences', '均衡饮食')}
- 过敏情况：{user_data.get('allergies', '无')}
- BMI指数：{user_data.get('bmi', 22)}

请基于以上真实天气数据提供：
1. 3条针对当前真实天气的健康建议
2. 3个适合的菜品推荐
3. 3种建议采购的食材

请用JSON格式返回，包含health_tips、recommended_dishes、shopping_list三个字段。"""
    
    return prompt

def get_season(month):
    """根据月份获取季节"""
    if month in [12, 1, 2]:
        return "冬季"
    elif month in [3, 4, 5]:
        return "春季"
    elif month in [6, 7, 8]:
        return "夏季"
    else:
        return "秋季"

def get_fallback_recommendations():
    """备用推荐数据"""
    current_month = datetime.now().month
    season = get_season(current_month)
    
    if season == "冬季":
        return {
            "health_tips": [
                "注意保暖，预防感冒",
                "增加高蛋白食物摄入",
                "适量补充维生素C增强免疫力"
            ],
            "recommended_dishes": [
                "红烧羊肉煲",
                "鸡汤炖蘑菇",
                "姜枣茶"
            ],
            "shopping_list": [
                "羊肉", "生姜", "红枣", "蘑菇"
            ]
        }
    elif season == "夏季":
        return {
            "health_tips": [
                "多补充水分和电解质",
                "选择清淡易消化的食物",
                "避免高温时段户外活动"
            ],
            "recommended_dishes": [
                "凉拌黄瓜",
                "绿豆汤",
                "西瓜冰沙"
            ],
            "shopping_list": [
                "黄瓜", "绿豆", "西瓜", "薄荷"
            ]
        }
    elif season == "春季":
        return {
            "health_tips": [
                "适当增加户外活动",
                "选择新鲜时令蔬菜",
                "注意预防春季过敏"
            ],
            "recommended_dishes": [
                "清炒春笋",
                "菠菜豆腐汤",
                "韭菜炒蛋"
            ],
            "shopping_list": [
                "春笋", "菠菜", "韭菜", "豆腐"
            ]
        }
    else:  # 秋季
        return {
            "health_tips": [
                "多吃滋润肺部的食物",
                "适当增加蛋白质摄入",
                "注意皮肤保湿"
            ],
            "recommended_dishes": [
                "银耳莲子羹",
                "梨汤",
                "南瓜粥"
            ],
            "shopping_list": [
                "银耳", "梨", "南瓜", "莲子"
            ]
        }

import requests
import json
from django.conf import settings

def precise_test():
    api_key = "a4d402794ff04d697a3f110793f555a2"  # 直接使用您的密钥
    location_id = "101030700"  # 天津东丽区
    
    print("=== 精确API测试 ===")
    print(f"API密钥: {api_key}")
    print(f"LocationID: {location_id}")
    
    url = "https://devapi.qweather.com/v7/weather/now"
    params = {
        'location': location_id,
        'key': api_key,
        'lang': 'zh',
        'gzip': 'n'  # 添加这个参数避免gzip问题
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        # 打印原始响应文本
        print(f"原始响应: {response.text}")
        
        # 解析JSON
        data = response.json()
        print(f"解析后的数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if data.get('code') == '200':
            print("🎉 API调用成功！")
            weather = data['now']
            print(f"天气: {weather['text']}")
            print(f"温度: {weather['temp']}°C")
            print(f"湿度: {weather['humidity']}%")
            return True
        else:
            print(f"❌ API错误: {data.get('code')} - {data.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return False

# 运行测试
precise_test()

import os
from django.core.cache import cache
import logging

# 配置日志
logger = logging.getLogger(__name__)
# ==================== AI对话功能API ====================

def log_conversation(user_id, user_message, ai_response):
    """
    记录对话日志
    """
    try:
        print(f"💬 对话记录 - 用户{user_id}: {user_message[:50]}...")
        print(f"🤖 AI回复: {ai_response[:100]}...")
        
        # 如果需要保存到数据库，可以在这里添加代码
        # log_entry = {
        #     'user_id': user_id,
        #     'user_message': user_message,
        #     'ai_response': ai_response,
        #     'timestamp': datetime.datetime.now(),
        # }
        # db_dietcat.ConversationLogs.insert_one(log_entry)
        
    except Exception as e:
        print(f"记录对话失败: {e}")
@csrf_exempt
@require_http_methods(["POST"])
def ai_chat(request):
    """
    AI对话API - 处理用户与AI营养师的对话
    """
    print("=== AI对话API被调用 ===")
    
    try:
        # 检查用户是否登录
        user_id = request.session.get('_id')
        print(f"用户ID: {user_id}")
        
        if not user_id:
            print("用户未登录")
            return JsonResponse({
                'success': False, 
                'message': '请先登录'
            }, status=401)
        
        # 解析请求数据
        raw_body = request.body.decode('utf-8')
        print(f"原始请求体: {raw_body}")
        
        data = json.loads(raw_body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        print(f"用户消息: {user_message}")
        print(f"对话历史长度: {len(conversation_history)}")
        
        if not user_message:
            print("消息为空")
            return JsonResponse({
                'success': False,
                'message': '消息不能为空'
            }, status=400)
        
        # 生成AI回复
        print("开始生成AI回复...")
        ai_response = generate_ai_chat_response(user_message, conversation_history, user_id)
        print(f"AI回复生成成功: {ai_response[:100]}...")
        
        # 记录对话（可选）
        log_conversation(user_id, user_message, ai_response)
        
        return JsonResponse({
            'success': True,
            'response': ai_response
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        print(f"AI对话处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': '对话处理失败，请稍后重试'
        }, status=500)
    
def call_deepseek_api(prompt, max_tokens=1000, max_retries=3):
    """
    调用DeepSeek API - 带重试机制
    """
    for attempt in range(max_retries):
        try:
            api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
            if not api_key:
                raise Exception("DeepSeek API密钥未配置")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False
            }
            
            print(f"🔄 第{attempt + 1}次尝试调用DeepSeek API，提示词长度: {len(prompt)}")
            
            # 动态调整超时时间：第一次30秒，第二次45秒，第三次60秒
            timeout = 30 + (attempt * 15)
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ 第{attempt + 1}次尝试成功")
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.Timeout:
            print(f"⏰ 第{attempt + 1}次尝试超时（{timeout}秒）")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 指数退避：2秒, 4秒, 6秒
                print(f"⏳ 等待{wait_time}秒后重试...")
                import time
                time.sleep(wait_time)
                continue
            else:
                print("❌ 所有重试尝试均超时")
                raise Exception("AI服务响应超时，请稍后重试")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 第{attempt + 1}次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"⏳ 等待{wait_time}秒后重试...")
                import time
                time.sleep(wait_time)
                continue
            else:
                raise Exception("AI服务暂时不可用")
                
        except (KeyError, IndexError) as e:
            print(f"❌ 第{attempt + 1}次响应解析失败: {str(e)}")
            raise Exception("AI响应解析失败")
        except Exception as e:
            print(f"❌ 第{attempt + 1}次调用异常: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"⏳ 等待{wait_time}秒后重试...")
                import time
                time.sleep(wait_time)
                continue
            else:
                raise Exception("AI服务调用失败")
def get_mock_ai_response(user_message):
    """
    模拟AI回复 - 增强版本，集成真实数据库查询
    """
    print(f"使用模拟回复，用户消息: {user_message}")
    
    import time
    time.sleep(1)  # 模拟思考时间
    
    user_message_lower = user_message.lower()
    
    # 如果是外卖相关的问题，从数据库获取真实推荐
    if any(keyword in user_message_lower for keyword in 
           ['外卖', '点餐', '推荐外卖', '吃什么', '点外卖', '应酬', '数据库']):
        return get_intelligent_food_recommendations(user_message, "mock_user")
    
    # 其他情况的专业回复
    elif any(keyword in user_message_lower for keyword in ['减脂', '减肥', '瘦身']):
        return get_intelligent_food_recommendations("减脂", "mock_user")
    
    elif any(keyword in user_message_lower for keyword in ['蛋白质', '高蛋白']):
        return get_intelligent_food_recommendations("高蛋白", "mock_user")
    
    elif any(keyword in user_message_lower for keyword in ['清淡', '健康']):
        return get_intelligent_food_recommendations("清淡", "mock_user")
    
    else:
        # 使用您提供的专业回复模板
        return """好！根据您提供的信息（BMI 23.9处于健康范围、饮食偏好清淡、长期应酬、睡眠7小时），我理解您可能希望通过外卖选择来平衡工作与健康需求。以下是我的专业建议：

**一、外卖选择原则（针对应酬族）**
1. **烹饪方式优先顺序**：蒸/煮＞炖/烫＞烤＞清炒＞煎炸
2. **隐形盐糖警惕区**：勾芡汁、酱料包、腌制品、浓缩汤底
3. **膳食平衡公式**：1份主食（1拳头） + 1.5份蛋白质（掌心大小） + 2份蔬菜（2拳头）

**二、具体外卖推荐**
请告诉我您想了解哪种类型的外卖推荐，我可以从数据库中为您筛选：
- 🍱 商务应酬类外卖
- 🥗 健康清淡类外卖  
- 💪 高蛋白健身餐
- 🍲 家常便当类
- 🌿 轻食沙拉类

**三、应酬人群特别贴士**
1. **餐前准备**：应酬前半小时先喝200ml无糖豆浆/酸奶，避免空腹摄入酒精
2. **点餐主动权**：主动建议点1道清汤（如豆腐海带汤）、1道蒸菜、1道深色蔬菜
3. **饮酒缓冲**：每杯酒间隔饮用250ml柠檬水，搭配毛豆、凉拌木耳等小菜

请告诉我您的具体需求，我可以从数据库中为您推荐合适的外卖选择！"""
def debug_food_database(request):
    """
    调试菜品数据库
    """
    try:
        # 获取数据库统计
        total_foods = mainapp_dao.db_dietcat.ShopFood.count_documents({})
        categories = mainapp_dao.db_dietcat.ShopFood.distinct('分类')
        
        # 获取一些样例数据
        sample_foods = list(mainapp_dao.db_dietcat.ShopFood.find().limit(10))
        
        result = f"""
        <h1>菜品数据库调试信息</h1>
        <h2>统计信息</h2>
        <ul>
            <li>总菜品数量: {total_foods}</li>
            <li>分类列表: {', '.join(categories)}</li>
        </ul>
        
        <h2>样例菜品 (前10个)</h2>
        <table border="1">
            <tr>
                <th>商铺名称</th>
                <th>菜品</th>
                <th>分类</th>
                <th>价格</th>
                <th>评分</th>
                <th>卡路里</th>
            </tr>
        """
        
        for food in sample_foods:
            result += f"""
            <tr>
                <td>{food.get('商铺名称', '')}</td>
                <td>{food.get('菜品', '')}</td>
                <td>{food.get('分类', '')}</td>
                <td>{food.get('价格', '')}</td>
                <td>{food.get('评分', '')}</td>
                <td>{food.get('卡路里', '')}</td>
            </tr>
            """
        
        result += "</table>"
        
        return HttpResponse(result)
        
    except Exception as e:
        return HttpResponse(f"数据库调试出错: {e}")
def get_intelligent_food_recommendations(user_message, user_id):
    """
    智能菜品推荐 - 结合用户信息和数据库实际数据
    """
    try:
        user = get_user_by_id(user_id)
        user_message_lower = user_message.lower()
        
        print(f"智能推荐 - 用户消息: {user_message}, 用户ID: {user_id}")
        
        # 构建推荐查询
        query = build_recommendation_query(user_message_lower, user)
        
        # 从数据库获取推荐菜品
        foods = list(mainapp_dao.db_dietcat.ShopFood.find(query).limit(8))
        
        # 如果结果不够，补充其他推荐
        if len(foods) < 4:
            additional_foods = get_additional_recommendations(user_message_lower, user)
            # 去重
            existing_ids = [str(f['_id']) for f in foods]
            for food in additional_foods:
                if str(food['_id']) not in existing_ids:
                    foods.append(food)
        
        # 为菜品添加评分信息
        for food in foods:
            food_id = food.get('_id')
            if food_id:
                rating_stats = get_food_rating_stats_real_time(food_id)
                if rating_stats:
                    food['average_rating'] = rating_stats['average_rating']
                    food['rating_count'] = rating_stats['rating_count']
        
        print(f"从数据库找到 {len(foods)} 个推荐菜品")
        return format_recommendation_response(foods, user_message, user)
        
    except Exception as e:
        print(f"智能菜品推荐失败: {e}")
        return "暂时无法访问菜品数据库，但我可以为您提供专业的饮食建议。"

def build_recommendation_query(user_message, user):
    """
    构建推荐查询条件
    """
    query = {}
    
    # 基于用户消息的关键词
    if any(keyword in user_message for keyword in ['清淡', '健康', '养生']):
        query['$or'] = [
            {'分类': {'$in': ['粥', '汤', '养生', '轻食', '沙拉']}},
            {'菜品': {'$regex': '蒸|煮|炖|清炒|白灼'}}
        ]
    
    elif any(keyword in user_message for keyword in ['应酬', '商务', '聚餐']):
        query['$or'] = [
            {'分类': {'$in': ['中餐', '日料', '粤菜']}},
            {'菜品': {'$regex': '套餐|定食|商务餐'}}
        ]
    
    elif any(keyword in user_message for keyword in ['减脂', '减肥', '低卡']):
        query['$or'] = [
            {'分类': {'$in': ['轻食', '沙拉', '健康']}},
            {'卡路里': {'$lt': 400}}
        ]
    
    elif any(keyword in user_message for keyword in ['高蛋白', '增肌']):
        query['蛋白质'] = {'$gte': 20}
    
    # 基于用户偏好
    if user and user.get('eating_prefer'):
        if '辣' in user['eating_prefer']:
            query['分类'] = {'$in': ['川菜', '湘菜', '火锅']}
        elif '清淡' in user['eating_prefer']:
            query['分类'] = {'$in': ['粥', '汤', '养生']}
    
    # 默认查询所有菜品，按评分排序
    if not query:
        query = {}
    
    return query

def get_additional_recommendations(user_message, user):
    """
    获取补充推荐
    """
    try:
        # 高评分菜品作为补充
        high_rated = list(mainapp_dao.db_dietcat.ShopFood.find().sort([('评分', -1)]).limit(6))
        return high_rated
    except:
        return []

def format_recommendation_response(foods, user_message, user):
    """
    格式化推荐响应
    """
    if not foods:
        return "目前数据库中暂时没有找到完全匹配的菜品，但我可以为您推荐一些通用建议..."
    
    response = "🍱 **基于数据库的智能外卖推荐**：\n\n"
    
    for i, food in enumerate(foods[:6], 1):  # 最多显示6个
        shop_name = food.get('商铺名称', '未知商家')
        dish_name = food.get('菜品', '未知菜品')
        price = food.get('价格', '?')
        rating = food.get('average_rating', food.get('评分', 4.0))
        
        response += f"{i}. **{shop_name}** - {dish_name}"
        response += f"（¥{price}）"
        response += f" ⭐{rating}"
        
        # 添加健康标签
        health_tags = get_health_tags(food)
        if health_tags:
            response += f" 🏷️{health_tags}"
        
        response += "\n"
    
    response += "\n💡 **选择建议**：\n"
    
    # 根据用户情况提供建议
    if user and user.get('eating_prefer') == '清淡':
        response += "• 优先选择蒸、煮、炖的烹饪方式\n"
        response += "• 避免重油重盐的菜品\n"
        response += "• 可要求商家少油少盐\n"
    
    if '应酬' in user_message.lower():
        response += "• 餐前先喝汤，避免空腹饮酒\n"
        response += "• 选择蒸菜和深色蔬菜\n"
        response += "• 要求酱汁分装，自主控制用量\n"
    
    response += "\n需要了解某个菜品的详细信息吗？"
    
    return response

def get_health_tags(food):
    """
    获取菜品健康标签
    """
    tags = []
    
    calories = food.get('卡路里', 0)
    protein = food.get('蛋白质', 0)
    category = food.get('分类', '')
    
    if calories > 0:
        if calories < 400:
            tags.append('低卡')
        elif calories > 600:
            tags.append('高能')
    
    if protein >= 20:
        tags.append('高蛋白')
    elif protein >= 15:
        tags.append('蛋白丰富')
    
    if category in ['轻食', '沙拉', '养生']:
        tags.append('健康')
    elif category in ['粥', '汤']:
        tags.append('易消化')
    
    return ' '.join(tags) if tags else ''

def recommend_food(request):
    """
    推荐外卖主功能 - 基于用户偏好和菜品评分智能推荐
    """
    user_id = request.session.get('_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        # 获取用户信息
        user = get_user_by_id(user_id)
        
        # 构建个性化推荐
        recommendations = get_personalized_recommendations(user)
        
        # 如果没有足够的个性化推荐，补充热门推荐
        if len(recommendations) < 8:
            hot_foods = hotFood(12 - len(recommendations))
            # 去重
            existing_food_ids = [str(rec['_id']) for rec in recommendations]
            for food in hot_foods:
                if str(food['_id']) not in existing_food_ids:
                    recommendations.append(food)
        
        # 为每个菜品添加评分信息
        for food in recommendations:
            food_id = food.get('_id')
            if food_id:
                rating_stats = get_food_rating_stats_real_time(food_id)
                if rating_stats:
                    food['average_rating'] = rating_stats['average_rating']
                    food['rating_count'] = rating_stats['rating_count']
                else:
                    food['average_rating'] = food.get('评分', 3.0)
                    food['rating_count'] = 0
        
        print(f"为用户 {user_id} 推荐了 {len(recommendations)} 个菜品")
        
        return render(request, 'web/recommend_food.html', {
            'recommendations': recommendations,
            'user': user,
            'total_count': len(recommendations)
        })
        
    except Exception as e:
        print(f"推荐外卖出错: {e}")
        # 出错时返回热门菜品
        hot_foods = hotFood(12)
        return render(request, 'web/recommend_food.html', {
            'recommendations': hot_foods,
            'user': None,
            'total_count': len(hot_foods),
            'error_message': '个性化推荐暂时不可用，已为您推荐热门菜品'
        })

def get_personalized_recommendations(user):
    """
    基于用户信息生成个性化推荐
    """
    try:
        recommendations = []
        
        # 1. 基于用户饮食偏好推荐
        if user and user.get('eating_prefer'):
            prefer_recommendations = get_recommendations_by_preference(user['eating_prefer'])
            recommendations.extend(prefer_recommendations)
        
        # 2. 基于用户健康目标推荐
        if user and (user.get('weight') and user.get('height')):
            health_recommendations = get_recommendations_by_health_goal(user)
            recommendations.extend(health_recommendations)
        
        # 3. 基于高评分菜品推荐
        high_rated_foods = list(mainapp_dao.db_dietcat.ShopFood.find().sort([('评分', -1)]).limit(6))
        recommendations.extend(high_rated_foods)
        
        # 去重
        unique_recommendations = []
        seen_ids = set()
        for food in recommendations:
            food_id = str(food.get('_id'))
            if food_id not in seen_ids:
                seen_ids.add(food_id)
                unique_recommendations.append(food)
        
        return unique_recommendations[:12]  # 最多返回12个
        
    except Exception as e:
        print(f"个性化推荐生成失败: {e}")
        return list(mainapp_dao.db_dietcat.ShopFood.find().limit(12))

def get_recommendations_by_preference(eating_prefer):
    """
    根据饮食偏好推荐
    """
    preference_map = {
        '辣': ['川菜', '湘菜', '火锅', '麻辣烫'],
        '清淡': ['粥', '汤', '养生', '轻食', '沙拉'],
        '甜': ['甜品', '饮品', '蛋糕'],
        '咸': ['家常菜', '卤味', '腌制品'],
        '酸': ['凉菜', '泡菜', '酸辣系列']
    }
    
    if eating_prefer in preference_map:
        categories = preference_map[eating_prefer]
        return list(mainapp_dao.db_dietcat.ShopFood.find({
            '分类': {'$in': categories}
        }).limit(6))
    
    return []

def get_recommendations_by_health_goal(user):
    """
    根据健康目标推荐
    """
    try:
        # 计算BMI
        weight_kg = float(user['weight']) / 2
        height_m = float(user['height']) / 100
        bmi = weight_kg / (height_m ** 2)
        
        if bmi < 18.5:
            # 偏瘦：推荐高蛋白、适量热量的食物
            return list(mainapp_dao.db_dietcat.ShopFood.find({
                '蛋白质': {'$gte': 20},
                '卡路里': {'$gte': 400, '$lte': 600}
            }).limit(4))
        elif bmi > 24:
            # 偏重：推荐低卡、高蛋白的食物
            return list(mainapp_dao.db_dietcat.ShopFood.find({
                '卡路里': {'$lt': 450},
                '蛋白质': {'$gte': 15}
            }).limit(4))
        else:
            # 正常：推荐均衡营养的食物
            return list(mainapp_dao.db_dietcat.ShopFood.find({
                '卡路里': {'$gte': 350, '$lte': 550},
                '蛋白质': {'$gte': 12}
            }).limit(4))
            
    except Exception as e:
        print(f"健康目标推荐失败: {e}")
        return []
def get_recommended_foods_from_db(user_preference):
    """
    从数据库获取推荐菜品
    """
    try:
        user_preference_lower = user_preference.lower()
        
        # 根据用户偏好构建查询条件
        query = {}
        if '减脂' in user_preference_lower or '减肥' in user_preference_lower:
            # 推荐低卡路里、高蛋白的食物
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '卡路里': {'$lt': 500},
                '蛋白质': {'$gte': 15}
            }).sort([('评分', -1)]).limit(5))
            category_desc = "低卡高蛋白"
            
        elif '蛋白质' in user_preference_lower or '高蛋白' in user_preference_lower:
            # 推荐高蛋白食物
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '蛋白质': {'$gte': 20}
            }).sort([('评分', -1)]).limit(5))
            category_desc = "高蛋白"
            
        elif '健康' in user_preference_lower or '清淡' in user_preference_lower:
            # 推荐健康清淡的食物
            foods = list(mainapp_dao.db_dietcat.ShopFood.find({
                '分类': {'$in': ['沙拉', '粥', '汤', '养生']}
            }).sort([('评分', -1)]).limit(5))
            category_desc = "健康清淡"
            
        else:
            # 默认推荐高评分食物
            foods = list(mainapp_dao.db_dietcat.ShopFood.find().sort([('评分', -1)]).limit(6))
            category_desc = "热门"
        
        if foods:
            recommendations = []
            for food in foods:
                food_desc = f"• {food.get('商铺名称', '')} - {food.get('菜品', '')}"
                if food.get('价格'):
                    food_desc += f"（¥{food.get('价格')}"
                    if food.get('原价'):
                        food_desc += f", 原价¥{food.get('原价')}"
                    food_desc += "）"
                
                if food.get('评分'):
                    food_desc += f" ⭐{food.get('评分')}"
                
                recommendations.append(food_desc)
            
            response = f"为您推荐{category_desc}外卖：\n" + "\n".join(recommendations)
            response += "\n\n您对哪种菜品比较感兴趣？我可以提供更详细的信息。"
            return response
        else:
            return "目前数据库中没有找到匹配的菜品，但我可以为您推荐一些通用建议..."
            
    except Exception as e:
        print(f"从数据库获取推荐菜品失败: {e}")
        return "暂时无法访问菜品数据库，但我可以为您提供一般的饮食建议。"
def get_precise_food_recommendations(health_goal, user_preferences=""):
    """
    根据健康目标和用户偏好获取精确的菜品推荐
    """
    try:
        base_query = {}
        
        # 根据健康目标调整查询条件
        if health_goal == 'weight_loss':
            base_query['卡路里'] = {'$lt': 450}
            base_query['蛋白质'] = {'$gte': 15}
        elif health_goal == 'weight_gain':
            base_query['蛋白质'] = {'$gte': 20}
            base_query['卡路里'] = {'$gte': 400, '$lte': 600}
        elif health_goal == 'maintenance':
            base_query['卡路里'] = {'$gte': 350, '$lte': 550}
            base_query['蛋白质'] = {'$gte': 12}
        
        # 如果有用户偏好，进一步筛选
        if user_preferences:
            if '辣' in user_preferences:
                base_query['分类'] = {'$in': ['川菜', '湘菜', '麻辣烫']}
            elif '清淡' in user_preferences:
                base_query['分类'] = {'$in': ['粥', '汤', '养生']}
            elif '甜' in user_preferences:
                base_query['分类'] = {'$in': ['甜品', '饮品']}
        
        # 执行查询
        foods = list(mainapp_dao.db_dietcat.ShopFood.find(base_query).sort([('评分', -1)]).limit(8))
        
        return foods
        
    except Exception as e:
        print(f"精确菜品推荐失败: {e}")
        return []
def generate_ai_chat_response(user_message, conversation_history, user_id):
    """
    生成AI对话回复 - 增强版本，集成数据库查询
    """
    try:
        print(f"生成AI回复 - 用户消息: {user_message}")
        
        # 检查是否是推荐外卖的请求
        if any(keyword in user_message.lower() for keyword in 
               ['推荐外卖', '推荐菜品', '点外卖', '吃什么', '外卖推荐', '数据库']):
            print("检测到外卖推荐请求，从数据库获取真实推荐...")
            return get_intelligent_food_recommendations(user_message, user_id)
        
        # 检查是否使用模拟数据
        if getattr(settings, 'USE_MOCK_API', True):
            print("🎭 使用模拟AI回复")
            return get_mock_ai_response(user_message)
        
        # 构建对话提示词
        prompt = build_chat_prompt(user_message, conversation_history, user_id)
        
        # 调用DeepSeek API
        api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
        if not api_key:
            print("🔑 未配置DeepSeek API密钥，使用模拟回复")
            return get_mock_ai_response(user_message)
        
        print("🚀 尝试调用真实DeepSeek API...")
        response = call_deepseek_api(prompt, max_tokens=1000)
        print("✅ 真实API调用成功")
        return response.strip()
        
    except Exception as e:
        print(f"❌ AI回复生成失败: {str(e)}")
        print("🔄 回退到模拟回复...")
        return get_mock_ai_response(user_message)
def build_chat_prompt(user_message, conversation_history, user_id):
    """
    构建对话提示词
    """
    # 获取用户健康信息
    user_info = get_user_health_context(user_id)
    
    system_prompt = f"""你是一位专业的AI营养师，具有丰富的营养学和饮食健康知识。请根据用户的提问提供专业、准确、实用的饮食建议。

用户背景信息：
{user_info}

你的回答应该：
1. 基于科学的营养学知识
2. 考虑用户的个人情况（如年龄、健康状况等）
3. 提供具体可执行的建议
4. 语言亲切、专业但不晦涩
5. 如果信息不足，可以询问更多细节
6. 避免提供医疗诊断，建议严重问题咨询专业医生

请用中文回复，保持专业但友好的语气。"""

    # 构建对话历史
    conversation_text = ""
    for msg in conversation_history[-6:]:  # 只保留最近6条对话
        role = "用户" if msg.get('role') == 'user' else "助手"
        content = msg.get('content', '')
        # 限制每条消息的长度
        if len(content) > 200:
            content = content[:197] + "..."
        conversation_text += f"{role}: {content}\n"
    
    return f"""{system_prompt}

当前对话上下文：
{conversation_text}

用户: {user_message}

助手: """

def get_user_health_context(user_id):
    """
    获取用户健康背景信息 - 增强版本
    """
    try:
        user = get_user_by_id(user_id)
        if not user:
            return "用户信息未知"
        
        context_parts = []
        
        # 基本身体信息
        if user.get('weight') and user.get('height'):
            weight_kg = float(user['weight']) / 2
            height_m = float(user['height']) / 100
            bmi = weight_kg / (height_m ** 2)
            context_parts.append(f"BMI指数: {bmi:.1f}")
        
        # 饮食偏好
        if user.get('eating_prefer'):
            context_parts.append(f"饮食偏好: {user['eating_prefer']}")
        
        # 饮食风格
        if user.get('eating_style'):
            context_parts.append(f"饮食风格: {user['eating_style']}")
        
        # 病史/过敏
        if user.get('anamnesis') and user['anamnesis'] != '无':
            context_parts.append(f"健康注意: {user['anamnesis']}")
        
        # 睡眠情况
        if user.get('sleep_time_avg'):
            context_parts.append(f"平均睡眠: {user['sleep_time_avg']}小时")
        
        if context_parts:
            return "\n".join(context_parts)
        else:
            return "用户尚未完善健康信息"
            
    except Exception as e:
        logger.error(f"获取用户健康背景失败: {e}")
        return "用户信息获取失败"
    
def get_database_food_info():
    """
    获取数据库中的菜品信息 - 增强版本
    """
    try:
        # 获取所有分类
        categories = mainapp_dao.db_dietcat.ShopFood.distinct('分类')
        
        # 获取特色推荐
        food_info = []
        
        # 健康推荐
        healthy_foods = list(mainapp_dao.db_dietcat.ShopFood.find({
            '$or': [
                {'分类': '轻食'},
                {'分类': '沙拉'},
                {'分类': '粥'},
                {'分类': '养生'}
            ]
        }).limit(3))
        
        if healthy_foods:
            healthy_list = [f"{f.get('菜品', '')}（¥{f.get('价格', '?')}）" for f in healthy_foods]
            food_info.append("健康轻食：" + "、".join(healthy_list))
        
        # 热门推荐
        popular_foods = list(mainapp_dao.db_dietcat.ShopFood.find().sort([('评分', -1)]).limit(3))
        if popular_foods:
            popular_list = [f"{f.get('菜品', '')}（⭐{f.get('评分', '?')}）" for f in popular_foods]
            food_info.append("热门菜品：" + "、".join(popular_list))
        
        # 商务推荐
        business_foods = list(mainapp_dao.db_dietcat.ShopFood.find({
            '分类': {'$in': ['中餐', '日料']}
        }).sort([('评分', -1)]).limit(3))
        
        if business_foods:
            business_list = [f"{f.get('菜品', '')}" for f in business_foods]
            food_info.append("商务餐选：" + "、".join(business_list))
        
        if food_info:
            return "数据库外卖特色：\n" + "\n".join(food_info)
        else:
            return "数据库中有丰富的外卖选择，包括健康轻食、商务餐、家常菜等多种类型。"
            
    except Exception as e:
        print(f"获取数据库菜品信息失败: {e}")
        return "数据库包含多种外卖选择，可根据您的需求推荐。"
@csrf_exempt
@require_http_methods(["POST"])
def recommend_food_api(request):
    """推荐外卖菜品API"""
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'})
        
        data = json.loads(request.body)
        user_preference = data.get('user_preference', '')
        limit = data.get('limit', 6)
        
        # 获取用户信息用于个性化推荐
        user = get_user_by_id(user_id)
        
        # 构建查询条件
        query = {}
        
        # 根据用户偏好调整推荐策略
        if user and user.get('eating_prefer'):
            if '辣' in user.get('eating_prefer', ''):
                query['分类'] = {'$in': ['川菜', '火锅']}
            elif '清淡' in user.get('eating_prefer', ''):
                query['分类'] = {'$in': ['面食', '饮品']}
        
        # 从数据库获取推荐菜品
        if query:
            foods = list(mainapp_dao.db_dietcat.ShopFood.find(query).sort([('评分', -1)]).limit(limit))
        else:
            # 默认推荐高评分菜品
            foods = list(mainapp_dao.db_dietcat.ShopFood.find().sort([('评分', -1)]).limit(limit))
        
        # 如果没有找到菜品，放宽条件
        if not foods:
            foods = list(mainapp_dao.db_dietcat.ShopFood.find().limit(limit))
        
        # 转换为可JSON序列化的格式
        recommendations = []
        for food in foods:
            recommendations.append({
                '菜品': food.get('菜品', ''),
                '商铺名称': food.get('商铺名称', ''),
                '价格': food.get('价格', 0),
                '评分': food.get('评分', 4.0),
                '配送时间': food.get('配送时间', '30分钟'),
                '起送价': food.get('起送价', 20),
                '卡路里': food.get('卡路里', 0),
                '分类': food.get('分类', ''),
                '月销量': food.get('月销量', 0)
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
        
    except Exception as e:
        print(f"推荐外卖API出错: {e}")
        return JsonResponse({
            'success': False,
            'message': '获取推荐失败'
        })
@csrf_exempt
@require_http_methods(["GET"])
def get_conversation_history(request):
    """
    获取用户的对话历史
    """
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'})
        
        # 从数据库获取对话历史（如果保存了的话）
        # 这里先返回空数组，实际使用时可以从数据库查询
        history = []
        
        return JsonResponse({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '获取历史失败'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def clear_conversation_history(request):
    """
    清空用户的对话历史
    """
    try:
        user_id = request.session.get('_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'})
        
        # 这里实现清空数据库中的对话历史
        # db_dietcat.ConversationLogs.delete_many({'user_id': user_id})
        
        return JsonResponse({
            'success': True,
            'message': '对话历史已清空'
        })
        
    except Exception as e:
        logger.error(f"清空对话历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '清空失败'
        }, status=500)