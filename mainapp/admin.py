# mainapp/admin.py
from django.contrib import admin
from .models import Category, Food, Rating

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'average_rating']
    list_filter = ['category']
    search_fields = ['name']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'food', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']