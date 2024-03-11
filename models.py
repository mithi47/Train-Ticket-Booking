from django.db import models
from datetime import date
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import JSONField

from django.contrib.auth.models import AbstractUser, Group
from django.core.validators import MinValueValidator, MaxValueValidator

from django.db import models


class Seat(models.Model):
    train = models.ForeignKey('Train', related_name='seats', on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)
    class_type = models.CharField(max_length=20)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.seat_number} - {self.train} - {self.class_type}"


class Train(models.Model):
    train_number = models.CharField(max_length=50)
    from_location = models.CharField(max_length=100)
    to_location = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    date = models.DateField(default=date.today)
    dep_time = models.TimeField(default='00:00')
    arr_time = models.TimeField(default='00:00')

    def __str__(self):
        return f"{self.train_number} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.pk:
            super(Train, self).save(*args, **kwargs)

            classes = ['Class1', 'Class2', 'Class3', 'Class4', 'Class5', 'Class6']
            for class_type in classes:
                for i in range(1, 31):
                    seat_number = f"{class_type}-{i}"
                    Seat.objects.create(train=self, seat_number=seat_number, class_type=class_type)
        else:
            super(Train, self).save(*args, **kwargs)


class Bookings(models.Model):
    user = models.ForeignKey(User, related_name='bookings', on_delete=models.CASCADE)
    train = models.ForeignKey(Train, related_name='bookings', on_delete=models.CASCADE)
    seats = JSONField(default=list)  # Store booked seat numbers as JSON array
    booking_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Booking #{self.id} - User: {self.user.username}, Train: {self.train.train_number}, Seats: {self.seats}"
