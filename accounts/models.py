from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Role(models.Model):
    roleName = models.CharField(max_length=50)

    def __str__(self):
        return self.roleName
class Customer(models.Model):
    GENDER_CHOICES = [
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
        ('Khác', 'Khác'),
    ]# (tuple (giá trị lưu trong database, giá trị hiển thị))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    #lien ket 1-1 voi User , nếu user bị xóa thì customer cũng bị xóa theo và cho phép truy cập ngược từ User đến Customer thông qua related_name
    fullName = models.CharField(max_length=100)
    phoneNumber = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True, null=True)
    dateOfBirth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Nam')


    def __str__(self):
        return self.fullName
    
    def viewBalance(self):
        if hasattr(self, 'wallet'):
            return self.wallet.balance
        return 0
    def createTopUpRequest(self, amount, note=''):
        if amount <= 0:
            raise ValueError("Số tiền nạp phải lớn hơn 0")
        return TopUpRequest.objects.create(
            customer=self,
            amount=amount,
            note=note,
            status='PENDING'
        )
class Wallet(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wallet')
    balance = models.PositiveBigIntegerField(default=0)
    def __str__(self):
        return f"Ví của {self.customer.fullName}"
class TopUpRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('APPROVED', 'APPROVED'),
        ('REJECTED', 'REJECTED'),
    ]
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='topup_requests')
    amount = models.PositiveBigIntegerField()
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    def __str__(self):
        return f"{self.customer.fullName} - {self.amount} - {self.status}"
