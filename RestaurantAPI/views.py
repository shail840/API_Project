from django.shortcuts import render
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Cart, Category, Order, OrderItem, MenuItem
from .serializers import CartSerializer, CategorySerializer, MenuItemSerializer, OrderItemSerializer, UserSerializer, OrderSerializer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group, User

# Create your views here.
class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    def get_permissions(self):
        permission_classes = []
        if self.request.method == 'GET':
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]


class MenuItemView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    search_fields = ['category','title']
    ordering_fields = ['price','inventory']
    
    def get_permissions(self):
        permission_classes = []
        if self.request.method == 'GET':
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    
    def get_permissions(self):
        permission_classes = []
        if self.request.method == 'GET':
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    

class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.all().filter(user=self.request.user)
    
    def delete(self,request,*args,**kwargs):
        Cart.objects.all().filter(user=self.request.user).delete()
        return Response("ok")
    
class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Order.objects.all()
        elif self.request.user.groups.count()==0:
            return Order.objects.all().filter(user=self.request.user)
        elif self.request.user.groups.filter(name='delivery_crew').exists():
            return Order.objects.all().filter(delivery_crew=self.request.user)
        else:
            return Order.objects.all()
    
    def create(self,request,*args,**kwargs):
        menuitem_count = Cart.objects.all().filter(user=self.request.user).count()
        if menuitem_count == 0:
            return Response({"message":"no, item in the cart"})
        data = request.data.copy()
        total = self.get_total_price(self.request.user)
        data['total'] = total
        data['user']  = self.request.user.id
        order_serializer = OrderSerializer(data=data)
        if (order_serializer.is_valid()):
            order = order_serializer.save()
            
            items = Cart.objects.all().filter(user=self.request.user).all()
            
            for item in items.values():
                orderitem = OrderItem(
                    order = order, 
                    menuitem_id = item['menuitem'],
                    price = item['price'],
                    quantity = item ['quantity'],
                )
                orderitem.save()
            Cart.objects.all().filter(user=self.request.user).delete()
            
            result = order_serializer.data.copy()
            result['total'] = total
            return Response(order_serializer.data)
        
    def get_total_price(self,user):
        total = 0
        items = Cart.objects.all().filter(user=user).all()
        for item in items.values():
            total = total + item['price']
        return total
    
    
class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def update(self,request,*args,**kwargs):
        if self.request.user.groups.count() == 0:
            return Response("Not Ok")
        else:
            return super().update(request,*args,**kwargs)
        
class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    def list(self,request):
        users = User.objects.all().filter(groups__name='Manager')
        items = UserSerializer(users, many=True)
        return Response(items.data)
    
    def create(self,request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.add(user)
        return Response({"message":"user added to the manager group"},status.HTTP_200_OK)
    
    def destroy(self,request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Managers")
        managers.user_set.remove(user)
        return Response({"message":"user removed from the manager group"},status.HTTP_200_OK)
    
    
class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self,request):
        users = User.objects.all().filter(gruops__name='Delivery Crew')
        items = UserSerializer(users, many=True)
        return Response(items.data)
    
    def create(self,request):
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists()==False:
                return Response({"message":"forbidden"},status.HTTP_403_FORBIDDEN)
        
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery Crew")
        dc.user_set.add(user)
        return Response({"message":"user added to the delivery crew group"},status.HTTP_200_OK)
    
    def destroy(self,request):
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name="Manager").exists()==False:
                return Response({"message":"forbidden"},status.HTTP_403_FORBIDDEN)
            
            user = get_object_or_404(User, username=request.data['username'])
            dc = Group.objects.get(name="Delivery Crew")
            dc.user_set.remove(user)
            return Response({"message":"user removed from delivery crew"},status.HTTP_200_OK)