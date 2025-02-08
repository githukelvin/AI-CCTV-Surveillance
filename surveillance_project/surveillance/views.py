import os
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .forms import VideoUploadForm, CustomUserCreationForm
from .models import Camera, Alert
from .utils.VideoFeed import VideoCamera, gen
from .utils.cctvConnection import VideoCameraCCTV, genCCTV
from .utils.fileUploadHandler import process_uploaded_video, VideoFileHandler
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib import messages
import json

from django.conf import settings

from .utils.path_handlers import get_media_url


@login_required
def dashboard(request):
    cameras = Camera.objects.filter(is_active=True)
    recent_alerts = Alert.objects.all()[:10]
    context = {
        'cameras': cameras,
        'recent_alerts': recent_alerts,
    }
    return render(request, 'dashboard/index.html', context)

@login_required
def video_feed(request):
    try:
        camera = VideoCamera()
        return StreamingHttpResponse(
            gen(camera),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")
@login_required
def index(request):
    return render(request, 'video/index.html')


@csrf_exempt  # Exempt from CSRF protection for simplicity (INSECURE for production)
def video_feedCCTV(request):
    if request.method == 'POST':
        ip_address = request.POST.get('ip_address')
        port = request.POST.get('port')
        username = request.POST.get('username')
        password = request.POST.get('password')
        path = request.POST.get('path')  # Get the path from the form

        rtsp_url = f"rtsp://{username}:{password}@{ip_address}:{port}/{path}"
        try:
            return StreamingHttpResponse(genCCTV(VideoCameraCCTV(rtsp_url)),
                                        content_type='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            return render(request, 'video/error.html', {'error_message': str(e)}) # Render an error page
    return render(request, 'video/cctv.html')  # Initial page with form


@login_required
def filter_alerts(request):
    # Get filter parameters
    threat_type = request.GET.get('threat_type', '')

    # Start with all alerts
    alerts = Alert.objects.all()

    # Apply threat type filter if specified
    if threat_type:
        alerts = alerts.filter(threat_type=threat_type)

    # Add to context
    context = {
        'alerts': alerts,
        'threat_types': Alert.THREAT_TYPES,
        'selected_threat': threat_type,  # Pass back selected value
    }

    return render(request, 'alerts/alerts.html', context)
@login_required
def camera_list(request):
    cameras = Camera.objects.all()
    return render(request, 'camera/list.html', {'cameras': cameras})

@login_required
def alert_list(request):
    alerts = Alert.objects.all()
    context = {
        'threat_types': Alert.THREAT_TYPES,
        'alerts': alerts    }
    return render(request, 'alerts/list.html', context)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard') # Redirect to dashboard after login
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set email
            user.email = form.cleaned_data.get('email')
            user.save()

            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'auth/register.html', {'form': form})

@login_required
def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Initialize handlers
            file_handler = VideoFileHandler()

            try:
                # Save uploaded video
                video_info = file_handler.save_uploaded_video(request.FILES['video'])

                # Create result directory
                result_dir = file_handler.create_result_directory(video_info['filename'])

                # Process video
                results = process_uploaded_video(video_info['filepath'])

                # Save results
                result_file = os.path.join(result_dir, 'analysis_results.json')
                with open(result_file, 'w') as f:
                    json.dump(results, f, indent=2)

                # Store paths in session for result view
                request.session['video_path'] = video_info['filepath']
                request.session['result_path'] = os.path.relpath(result_file, settings.MEDIA_ROOT)

                return redirect('view_results')

            except Exception as e:
                messages.error(request, f"Error processing video: {str(e)}")
                return redirect('upload_video')
    else:
        form = VideoUploadForm()

    return render(request, 'upload/upload_video.html', {'form': form})


@login_required
def view_results(request):
    video_path = request.session.get('video_path')
    result_path = request.session.get('result_path')

    if not video_path or not result_path:
        messages.error(request, "No results found. Please upload a video first.")
        return redirect('upload_video')

    # Convert video path to proper media URL for template
    video_url = get_media_url(video_path)

    # Read results
    result_file = os.path.join(settings.MEDIA_ROOT, result_path)
    with open(result_file, 'r') as f:
        results = json.load(f)

    context = {
        'video_path': video_url,
        'results': results
    }

    return render(request, 'upload/view_results.html', context)