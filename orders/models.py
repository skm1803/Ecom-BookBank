from django.db import models
from carts.models import Cart
from .utils import unique_slug_generator
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save,post_save
from math import fsum

#from other modules
from billings.models import BillingProfile,Address

ORDER_STATUS_CHOICES = (
    ('created','Created'),
    ('paid','Paid'),
    ('shipped','Shipped'),
    ('refunded','Refunded')
)

class OrderManager(models.Manager):
    def new_or_get(self,billing_profile,cart_obj):
        order_qs = self.get_queryset().filter(
        billing_profile=billing_profile,
        cart=cart_obj,
        active=True,
        status='created')
        
        if order_qs.count() == 1:
            order_obj = order_qs.first()
            created = False
        else:
            #all other orders having same cart inactive
            old_order_qs = self.get_queryset().exclude(billing_profile=billing_profile).filter(cart=cart_obj,active=True)
            if old_order_qs.exists():
                old_order_qs.update(active=False)
            order_obj = self.model.objects.create(billing_profile=billing_profile,cart=cart_obj)
            created = True
        return order_obj,created


class Order(models.Model):
    billing_profile  = models.ForeignKey(BillingProfile,on_delete = models.SET_NULL,null=True) #I don't want to lose Orders so used SET_NULL instead of Cascade
    shipping_address = models.ForeignKey(Address,on_delete = models.SET_NULL,related_name= "shipping_address",null=True,blank=True)
    billing_address  = models.ForeignKey(Address,on_delete = models.SET_NULL,related_name= "billing_address",null=True,blank=True)
    order_id         = models.CharField(max_length = 120,blank=True)
    cart             = models.ForeignKey(Cart,on_delete = models.SET_NULL,null=True)
    status           = models.CharField(max_length=120,default='created')
    shipping_total   = models.DecimalField(default=9.99,max_digits=9,decimal_places=2)
    total            = models.DecimalField(default=0.00,max_digits=9,decimal_places=2)
    active           = models.BooleanField(default=True)

    objects = OrderManager()

    def __str__(self):
        return self.order_id

    def update_total(self):
        '''this changes order total when cart changes its size or when order is created'''
        cart_total = self.cart.total
        shipping_total = self.shipping_total
        new_total = format(fsum([cart_total,shipping_total]),'.2f')
        self.total = new_total
        self.save()
        return new_total

    def check_done(self):
        billing_profile = self.billing_profile
        shipping_address= self.shipping_address
        billing_address = self.billing_address
        total           = self.total
        if self.total<0:
            return ValidationError("Suspicious Activity")
            print("mail with user credentials to admin and make user inactive")
        if billing_profile and shipping_address and billing_address:
            return True
        return False

    def mark_paid(self):
        if self.check_done():
            self.status = "paid"
            self.save()
        return self.status



def pre_save_create_order_id(sender,instance,*args,**kwargs):
    if not instance.order_id:
        instance.order_id = unique_slug_generator(instance)

pre_save.connect(pre_save_create_order_id,sender = Order)

def post_save_cart_total(sender,instance,created,*args,**kwargs):
    '''to update order object when cart changes its size'''
    if not created:
        print("rancart")
        cart_obj = instance
        cart_total = cart_obj.total
        cart_id    = cart_obj.id
        qs         = Order.objects.filter(cart__id = cart_id)
        if qs.count() == 1:
            order_obj = qs.first()
            order_obj.update_total()

post_save.connect(post_save_cart_total,sender = Cart)


def post_save_order(sender,instance,created,*args,**kwargs):
    print("ranout")
    if created:
        print("ranin")
        instance.update_total()

post_save.connect(post_save_order,sender = Order)
