from datetime import datetime, timedelta, timezone
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.mail import send_mail

from .models import Train, Seat, Bookings
import logging


def home(request):
    return render(request, 'home.html')


def registration(request):
    error_message = None

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if user already exists
        if User.objects.filter(username=name).exists():
            error_message = 'User with this name already exists.'
        else:
            # If user doesn't exist, create new user
            user = User.objects.create_user(username=name, email=email, password=password)
            user.save()

            return redirect('user_login')

    return render(request, 'registration.html', {'error_message': error_message})


def user_login(request):
    error_message = None
    if request.method == 'POST':
        name = request.POST['name']
        password = request.POST['password']

        user = authenticate(username=name, password=password)

        if user is not None:
            login(request, user)
            return redirect('/dash/')
        else:
            error_message = 'Username or password is incorrect.'

            return render(request, 'login.html', {'error_message': error_message})

    return render(request, 'login.html')


def dash(request):
    current_time = datetime.now()

    # Fetch trains where the departure date and time is in the future
    future_trains = Train.objects.filter(date__gte=current_time.date()).exclude(
        date=current_time.date(), dep_time__lt=current_time.time()
    )

    return render(request, 'dash.html', {'trains': future_trains})


def search_train(request):
    error_message = None
    trains = None

    if request.method == 'GET':
        current_time = datetime.utcnow()
        one_hour_later = current_time + timedelta(hours=1)

        from_location = request.GET.get('from')
        to_location = request.GET.get('to')
        date = request.GET.get('date')

        if from_location and to_location and date:
            if date == current_time.date():
                trains = Train.objects.filter(
                    from_location=from_location,
                    to_location=to_location,
                    date=date,
                    dep_time__gte=one_hour_later.time()
                )
            else:
                trains = Train.objects.filter(
                    from_location=from_location,
                    to_location=to_location,
                    date=date,
                )

            if not trains:
                error_message = 'No trains are available for the required date.'
                trains = Train.objects.filter(date__gte=current_time.date()).exclude(
                    date=current_time.date(), dep_time__lt=current_time.time()
                )

    return render(request, 'dash.html', {'trains': trains, 'error_message': error_message})


def book(request, train_number):
    train = Train.objects.get(train_number=train_number)
    seats = Seat.objects.filter(train=train)
    return render(request, 'book.html', {'seats': seats, 'train': train})


def book_seat(request):
    if request.method == 'POST':
        class_type = request.POST.get('class_type')
        seat_numbers = request.POST.get('seat_numbers')
        train_id = request.POST.get('train_id')

        # Get the logged-in user
        user = request.user

        train = Train.objects.get(train_number=train_id)
        selected_seats = seat_numbers.split(',')

        # Create a booking record for the user
        booking = Bookings.objects.create(user=user, train=train, seats=selected_seats)

        # Loop through each selected seat and update its status to booked
        for seat_number in selected_seats:
            seat = Seat.objects.get(train=train, seat_number=seat_number)
            seat.is_booked = True
            seat.save()

        # Constructing URL for confirmation view with booking ID included
        return redirect(reverse('confirmation', args=(booking.id, user.email, user.username, train.train_number)))


def get_seats(request, train_id):
    # Fetch seats for the specified train
    seats = Seat.objects.filter(train__train_number=train_id).values('seat_number', 'is_booked')
    # Convert QuerySet to a list of dictionaries
    seat_data = list(seats)
    # Return the seat data as JSON response
    return JsonResponse(seat_data, safe=False)


def confirm(request, booking_id, email, username, train_number):
    # Retrieve the booking details based on the booking ID
    booking = Bookings.objects.filter(id=booking_id).first()
    if booking:
        # Fetch seats associated with the booking
        seats = Seat.objects.filter(train=booking.train, seat_number__in=booking.seats)

        subject = 'Train Ticket Booking Successful'
        message = f'Hello {username},\n\nYour train ticket booking was successful.\n\nBooking Details:\n\n' \
                  f'Train Number: {booking.train.train_number}\n' \
                  f'Train Name: {booking.train.name}\n' \
                  f'From: {booking.train.from_location}\n' \
                  f'To: {booking.train.to_location}\n' \
                  f'Departure Date: {booking.train.date}\n' \
                  f'Departure Time: {booking.train.dep_time}\n' \
                  f'Arrival Time: {booking.train.arr_time}\n\n' \
                  f'Seats Booked:\n'

        for seat in seats:
            message += f'Seat Number: {seat.seat_number}, Class Type: {seat.class_type}\n'
        message += f'\nNumber of Seats Booked: {len(seats)}'

        message += f'\nThank you for booking with us.\nHave a safe journey\n\nBest regards,\nTrain Ticket Booking Application'

        from_email = 'manishmithilesh42@gmail.com'
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        return render(request, 'confirmation.html', {'booking': booking})


def delete_booking(request, booking_id):
    if request.method == 'POST':
        # Get the booking object or return 404 if not found
        booking = get_object_or_404(Bookings, id=booking_id)

        # Loop through each booked seat and update its status to not booked
        for seat_number in booking.seats:
            seat = Seat.objects.get(train=booking.train, seat_number=seat_number)
            seat.is_booked = False
            seat.save()

        # Delete the booking
        booking.delete()

    # Redirect to a desired URL, in this case, to the home page
    return redirect(reverse('booking_list'))


def booking_list(request):
    # Fetch bookings for the current logged-in user
    user_bookings = Bookings.objects.filter(user=request.user)

    # Filter bookings based on the departure time of the associated train
    valid_bookings = []
    current_time = datetime.now()

    for booking in user_bookings:
        # Check if the departure time of the train associated with the booking is in the future
        if booking.train.dep_time > current_time.time() or booking.train.date > current_time.date():
            valid_bookings.append(booking)

    # Pass the valid bookings to the template context
    context = {'bookings': valid_bookings}

    # Render the template with the valid bookings data
    return render(request, 'booking_list.html', context)


def logout_user(request):
    logout(request)
    return redirect('home')
