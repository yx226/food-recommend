# -*- coding: utf-8 -*-
"""
Created on Fri Aug 24 11:04:07 2018

@author: Durant
"""
import math
import numpy as np
import pymongo
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['dietcat']
posts = db.FoodEval


def get_info():
    client = MongoClient()
    client = MongoClient('localhost', 27017)
    db = client['dietcat']
    posts = db.FoodEval
    users = []
    foods = []
    FoodEval = []
    scotts_posts = posts.find({}, {"_id": 0})
    for post in scotts_posts:
        u = len(users)
        f = len(foods)
        if not post['用户'] in users:
            users.append(post['用户'])
            u += 1
            FoodEval.append([0 for i in range(f)])
        if not post['菜品'] in foods:
            foods.append(post['菜品'])
            f += 1
            for i in range(u):
                FoodEval[i].append(0)
        FoodEval[users.index(post['用户'])][foods.index(post['菜品'])] = post['评分']
    # print('FoodEval:\n', np.array(FoodEval))

    FoodSum = []
    b = np.transpose(FoodEval).tolist()
    for food in b:
        FoodSum.append(len(food) - food.count(0))
    # print('FoodSum:', FoodSum)

    FoodEval_bk = np.array(FoodEval).tolist()
    UserFood = []
    for i in FoodEval_bk:
        n = []
        for j in i:
            if j > 0:
                n.append(i.index(j))
                i[i.index(j)] = 0
        UserFood.append(n)
    # print('UserFood:', UserFood)

    FoodUser = []
    for i in b:
        n = []
        for j in i:
            if j > 0:
                n.append(i.index(j))
                i[i.index(j)] = 0
        FoodUser.append(n)
    # print('FoodUser:', FoodUser)
    print('数据库读取完成')
    return users, foods, FoodEval, FoodSum, UserFood, FoodUser


def TOPK_Index(L, k=5):
    Index_list = []
    for x in sorted(L, reverse=True)[0:k]:
        Index_list.append(L.index(x))
        L[L.index(x)] = 0
    return Index_list

def get_recommendation_by_bmi(user_id, base_recommendations):
    """根据BMI指数调整推荐"""
    user = mainapp_dao.firstDocInUser({"_id": ObjectId(user_id)})
    
    if user.get('weight') and user.get('height'):
        weight_kg = float(user['weight']) / 2  # 斤转公斤
        height_m = float(user['height']) / 100  # 厘米转米
        bmi = weight_kg / (height_m ** 2)
        
        # 根据BMI调整推荐
        if bmi < 18.5:  # 偏瘦
            return enhance_for_weight_gain(base_recommendations)
        elif bmi > 24:  # 超重
            return enhance_for_weight_loss(base_recommendations)
        else:  # 正常
            return enhance_for_health_maintenance(base_recommendations)
    
    return base_recommendations

def enhance_for_weight_loss(recommendations):
    """为减重用户优化推荐"""
    # 优先推荐低卡路里、高蛋白食物
    low_calorie_foods = []
    for food in recommendations:
        if food.get('卡路里', 1000) < 400:  # 低卡路里
            low_calorie_foods.append(food)
    
    return low_calorie_foods if low_calorie_foods else recommendations

def get_recommendation_by_activity(user_id, base_recommendations):
    """根据用户运动量调整推荐"""
    # 获取用户近期的运动数据
    activity_data = mainapp_dao.weekspoleep(user_id, datetime.datetime.now().strftime('%Y-%m-%d'))
    avg_sport_hours = sum(activity_data[0]) / 7  # 平均每日运动时长
    
    if avg_sport_hours > 1.5:  # 运动量大
        return enhance_for_high_activity(base_recommendations)
    elif avg_sport_hours < 0.5:  # 运动量小
        return enhance_for_low_activity(base_recommendations)
    
    return base_recommendations

def enhance_for_high_activity(recommendations):
    """为高运动量用户优化推荐"""
    # 增加碳水化合物和蛋白质比例
    energy_foods = []
    for food in recommendations:
        carbs = food.get('碳水化合物', 0)
        protein = food.get('蛋白质', 0)
        if carbs > 30 and protein > 15:
            energy_foods.append(food)
    
    return energy_foods if energy_foods else recommendations
def enhance_for_weight_gain(recommendations):
    """为增重用户优化推荐"""
    # 优先推荐高蛋白、适量碳水食物
    high_protein_foods = []
    for food in recommendations:
        if food.get('蛋白质', 0) > 20:  # 高蛋白
            high_protein_foods.append(food)
    
    return high_protein_foods if high_protein_foods else recommendations

class FoodRMD:
    def __init__(self):
        self.users, self.foods, self.FoodEval, self.FoodSum, self.UserFood, self.FoodUser = get_info()
        self.UserNum = len(self.users)
        self.FoodNum = len(self.foods)
        #        self.Weight=np.zeros((self.FoodNum,self.FoodNum))
        self.weight()
        self.Recommand()

    #        print(self.FoodEval)
    def weight(self):
        a = np.zeros((self.FoodNum, self.FoodNum))
        for i in range(self.FoodNum):
            for j in self.FoodUser[i]:
                a[i][self.UserFood[j]] += 1
        for i in range(self.FoodNum):
            a[i][i] = 0
        #        print(a)
        Max = 0
        self.Weight = np.zeros((self.FoodNum, self.FoodNum))
        for i in range(self.FoodNum):
            for j in range(self.FoodNum):
                self.Weight[i][j] = a[i][j] / math.sqrt(self.FoodSum[i] * self.FoodSum[j])
                if Max < self.Weight[i][j]:
                    Max = self.Weight[i][j]
        for i in range(self.FoodNum):
            for j in range(self.FoodNum):
                self.Weight[i][j] = self.Weight[i][j] / Max

    def Recommand(self):
        self.P = np.zeros((self.UserNum, self.FoodNum))
        for UserID in range(self.UserNum):
            for FoodID in range(self.FoodNum):
                if FoodID in self.UserFood[UserID]:
                    continue
                else:
                    for k in self.UserFood[UserID]:
                        self.P[UserID][FoodID] += self.Weight[FoodID][k] * self.FoodEval[UserID][k]
                self.P[UserID][FoodID] = self.P[UserID][FoodID] / len(self.UserFood[UserID])
        print('用户推荐矩阵计算完成')

    #        print(P)

    def All_Recommand(self, K=3):
        self.__init__()
        p = self.P.tolist()
        for UserID in range(self.UserNum):
            print(self.users[UserID], [self.foods[i] for i in TOPK_Index(p[UserID], K)])

    def Single_Recommand(self, User, K=1):
        self.__init__()
        p = self.P.tolist()
        UserID = self.users.index(User)
        return [self.foods[i] for i in TOPK_Index(p[UserID], K)]

    def AddEval(self, User, Food, score=1):
        if (posts.find_one({'用户': User, '菜品': Food})) is None:
            post_data = {'用户': User, '菜品': Food, '评分': score}
            result = posts.insert_one(post_data)
            print('One post: {0}'.format(result.inserted_id))
        else:
            posts.update_one({'用户': User, '菜品': Food}, {"$set": {'评分': score}})

    def AfferADD(self, User, Food, score=1):
        if not User in self.users:
            self.users.append(User)
            self.FoodEval.append([0 for i in range(self.FoodNum)])
            self.UserFood.append([])
            self.UserNum = len(self.users)
        if not Food in self.foods:
            self.foods.append(Food)
            for i in range(self.UserNum):
                self.FoodEval[i].append(0)
            self.FoodSum.append(1)
            self.FoodUser.append([])
            self.FoodNum = len(self.foods)
        else:
            self.FoodSum[self.foods.index(Food)] += 1
        self.FoodEval[self.users.index(User)][self.foods.index(Food)] = score
        if not self.foods.index(Food) in self.UserFood[self.users.index(User)]:
            self.UserFood[self.users.index(User)].append(self.foods.index(Food))
        if not self.users.index(User) in self.FoodUser[self.foods.index(Food)]:
            self.FoodUser[self.foods.index(Food)].append(self.users.index(User))
        self.UserNum = len(self.users)
        self.FoodNum = len(self.foods)
        self.weight()
        self.Recommand()


'''

RMD=FoodRMD()
print(RMD.users)
#print(RMD.Weight)
print(RMD.Single_Recommand('Tom'))
RMD.AddEval('Du','食物20',2)
RMD.AfferADD('Du','食物20',2)
print(RMD.All_Recommand())
print(RMD.Single_Recommand('Du'))

'''
