import numpy as np
from mainapp import dao as mainapp_dao
from bson.objectid import ObjectId

class HealthBasedRecommender:
    def __init__(self):
        self.health_factors = {}
    
    def calculate_health_score(self, user_id):
        """计算用户健康综合评分"""
        user = mainapp_dao.firstDocInUser({"_id": ObjectId(user_id)})
        
        scores = {
            'bmi_score': self._calculate_bmi_score(user),
            'activity_score': self._calculate_activity_score(user_id),
            'sleep_score': self._calculate_sleep_score(user_id),
            'diet_balance_score': self._calculate_diet_balance_score(user_id)
        }
        
        # 加权平均
        total_score = (scores['bmi_score'] * 0.4 + 
                      scores['activity_score'] * 0.3 + 
                      scores['sleep_score'] * 0.2 + 
                      scores['diet_balance_score'] * 0.1)
        
        return total_score, scores
    
    def _calculate_bmi_score(self, user):
        """计算BMI得分"""
        if user.get('weight') and user.get('height'):
            weight_kg = float(user['weight']) / 2
            height_m = float(user['height']) / 100
            bmi = weight_kg / (height_m ** 2)
            
            if 18.5 <= bmi <= 24:
                return 100  # 理想BMI
            elif 17 <= bmi < 18.5 or 24 < bmi <= 27:
                return 60   # 偏瘦或偏胖
            else:
                return 30   # 过瘦或肥胖
        return 50  # 默认分
    
    def _calculate_activity_score(self, user_id):
        """计算运动得分"""
        activity_data = mainapp_dao.weekspoleep(user_id, datetime.datetime.now().strftime('%Y-%m-%d'))
        avg_sport_hours = sum(activity_data[0]) / 7
        
        if avg_sport_hours >= 1:
            return 100
        elif avg_sport_hours >= 0.5:
            return 70
        else:
            return 40
    
    def recommend_by_health(self, user_id, base_recommendations, num=70):
        """基于健康数据的个性化推荐"""
        health_score, detailed_scores = self.calculate_health_score(user_id)
        
        # 根据健康评分调整推荐策略
        if health_score >= 80:
            return self._recommend_for_healthy_user(base_recommendations, num)
        elif health_score >= 60:
            return self._recommend_for_moderate_user(base_recommendations, num)
        else:
            return self._recommend_for_improvement_user(base_recommendations, num, detailed_scores)
    
    def _recommend_for_healthy_user(self, recommendations, num):
        """健康用户：维持均衡饮食"""
        # 优先选择营养均衡的食物
        balanced_foods = []
        for food in recommendations:
            protein = food.get('蛋白质', 0)
            carbs = food.get('碳水化合物', 0)
            fat = food.get('脂肪', 0)
            calories = food.get('卡路里', 0)
            
            # 均衡营养标准
            if (200 <= calories <= 600 and 
                protein >= 10 and 
                20 <= carbs <= 60 and 
                5 <= fat <= 25):
                balanced_foods.append(food)
        
        return balanced_foods[:num] if balanced_foods else recommendations[:num]
    
    def _recommend_for_improvement_user(self, recommendations, num, health_scores):
        """需要改善用户：针对性推荐"""
        improved_foods = []
        
        # 根据具体健康问题调整
        if health_scores['bmi_score'] < 60:
            # BMI不理想，控制热量
            for food in recommendations:
                calories = food.get('卡路里', 0)
                if health_scores['bmi_score'] < 40:  # 严重问题
                    if calories < 400:
                        improved_foods.append(food)
                else:  # 轻微问题
                    if calories < 550:
                        improved_foods.append(food)
        
        return improved_foods[:num] if improved_foods else recommendations[:num]