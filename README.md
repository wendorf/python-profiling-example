# Python Profiling Example with Scalene

A simple Flask-based image processing web service designed to demonstrate profiling with [Scalene](https://github.com/plasma-umass/scalene) on a live Render.com deployment. This app performs various CPU and memory-intensive image operations, making it ideal for understanding production performance characteristics.

## Why Profile?

Render provides excellent observability features for your services - metrics, logs, and health checks give you a great overview of your application's behavior. But sometimes you need to dig deeper. When your service is slow or using more resources than expected, you need detailed insights into what's happening inside your code.

**Profiling** is a powerful technique that shows you exactly where your application spends its time and resources. Unlike general metrics, a profiler gives you line-by-line breakdowns of:
- CPU usage (which functions are computational bottlenecks?)
- Memory allocation (where are you creating objects?)
- Python vs native code execution (are your libraries efficient?)

[Scalene](https://github.com/plasma-umass/scalene) is one of the best profiling tools for Python - it's fast, accurate, and provides beautiful HTML reports. In this guide, we'll show you how to take a normal Python web application deployed to Render and enhance it with profiling functionality, so you can understand exactly what's happening in your production service.

## The Example Application

This repository contains a simple Flask image processing service that applies various transformations to uploaded images - blur, sharpen, edge detection, and more. The service includes a CPU-intensive `noise_reduction` operation that's perfect for demonstrating profiling.

**What makes this good for profiling?**
- Mix of Python code and C extensions (PIL, numpy)
- Memory-intensive operations (image transformations)
- CPU-bound processing (noise reduction algorithms)
- Real HTTP request handling via Gunicorn

## Getting Started: Deploy to Render

First, let's get this application running on Render. You have two options:

**Option 1: Blueprint (Quickest)**

1. Fork or clone this repo to your GitHub account
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New" → "Blueprint"
4. Connect your repository
5. Render will automatically detect `render.yaml` and deploy your service

**Option 2: Manual Setup**

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3.11+

Once deployed, your service will be live at `https://your-service-name.onrender.com`. You can visit it in a browser to see the upload form, or hit the `/health` endpoint to verify it's running.

## Adding Profiling to Your Service

Now for the interesting part - let's add profiling! The magic happens with a simple configuration change that wraps your application with Scalene.

### Understanding the Wrapper

This repository includes `wrapper-app.py`, which runs your Flask application through Gunicorn in a way that Scalene can profile. The key is using a single Gunicorn worker process with threading - this keeps all your application code in one process where Scalene can see it, while still handling concurrent requests efficiently.

**For your own applications:** You'll likely need to adapt `wrapper-app.py` to match your setup:
- **Using uvicorn/FastAPI?** You'll need a similar wrapper that runs uvicorn programmatically with `workers=1`
- **Different web server?** The principle is the same - run it in a single process so Scalene can follow the code
- **Already using threading?** Great! Just ensure you're running with one worker process when profiling

The wrapper is just a pattern - adapt it to your stack. The core idea is always: single process + threading = profileable with Scalene.

### Step 1: Enable Profiling

Open your `render.yaml` and you'll see two `startCommand` lines:

```yaml
startCommand: gunicorn app:app
# To enable profiling, uncomment the line below and comment out the line above:
# startCommand: scalene --cpu --html --profile-interval=15 --outfile=/tmp/scalene.html wrapper-app.py
```

Simply swap the comments - comment out the `gunicorn` line and uncomment the `scalene` line:

```yaml
# startCommand: gunicorn app:app
startCommand: scalene --cpu --html --profile-interval=15 --outfile=/tmp/scalene.html wrapper-app.py
```

**If you're using manual deployment**, update your Start Command in the Render Dashboard instead:
```
scalene --cpu --html --profile-interval=15 --outfile=/tmp/scalene.html wrapper-app.py
```

**What do these Scalene options mean?**
- `--cpu` - Profile CPU usage only (less overhead than full profiling)
- `--html` - Generate a visual HTML report instead of text output
- `--profile-interval=15` - Sample the code every 15 seconds
- `--outfile=/tmp/scalene.html` - Save the report to this file path

### Step 2: Redeploy

Commit and push your changes (if using Blueprint), or trigger a manual redeploy from the Render Dashboard. Your service will now restart with Scalene watching every line of code that executes. The service will work exactly the same from the outside, but it's now quietly collecting performance data.

### Step 3: Generate Some Traffic

Now let's give your service some work to do. From your local machine, send some image processing requests:

```bash
# Set your service URL
SERVICE_URL="https://your-service-name.onrender.com"

# Send a single request (you'll need a test image - any JPG or PNG will work)
curl -X POST -F "image=@test_image.jpg" -F "operation=noise_reduction" \
  $SERVICE_URL/process --output result.jpg

# Or send multiple concurrent requests for more realistic profiling
for i in {1..10}; do
  curl -X POST -F "image=@test_image.jpg" -F "operation=noise_reduction" \
    $SERVICE_URL/process --output "result_$i.jpg" &
done
wait
```

You can also use the web interface by visiting your service URL in a browser and uploading images there.

**Let it run for a minute or two** - Scalene samples your code every 15 seconds, so the more requests you send over time, the better the profile data.

### Step 4: Get the Profile Report

Scalene has been writing its report to `/tmp/scalene.html` on your Render service. Now we need to download it.

First, get your SSH credentials from Render:

1. Go to your service in the [Render Dashboard](https://dashboard.render.com)
2. Click "Shell" in the left sidebar
3. Copy the SSH command - it'll look like: `ssh srv-cgrflmfdvk4n7bs16430@ssh.oregon.render.com`

Now use `scp` to download the file. Take your SSH command and transform it:
- Replace `ssh` with `scp`
- Add `:/tmp/scalene.html ./scalene.html` at the end

```bash
# If your SSH command was:
# ssh srv-cgrflmfdvk4n7bs16430@ssh.oregon.render.com

# Then your scp command is:
scp srv-cgrflmfdvk4n7bs16430@ssh.oregon.render.com:/tmp/scalene.html ./scalene.html
```

After downloading, open it in your browser:

```bash
open scalene.html  # macOS
# or
xdg-open scalene.html  # Linux
```

You'll see an HTML report showing exactly where your code spends its time. Check out [`scalene.html`](./scalene.html) in this repo to see an example.

### Step 5: Interpret the Results

The Scalene report shows line-by-line breakdowns of your application's performance. Here's how to read it and take action:

**Understanding the Columns:**
- **Time Python %** - Time spent in your Python code (this is what you can optimize)
- **Time native %** - Time in C extensions/libraries (usually already optimized)
- **Memory** - Allocations per line (look for unexpected large allocations)

**What to look for in your own service:**

1. **Hot spots** - Lines with high Python % are your optimization targets. These are where your code spends the most time.

2. **Unexpected bottlenecks** - Sometimes a seemingly simple line (like a list comprehension or JSON serialization) shows up as expensive. These are great finds.

3. **Native vs Python time** - If most time is "native", your libraries are doing the heavy lifting efficiently. If it's "Python", there might be room for optimization or switching to a compiled library.

4. **Memory patterns** - Large allocations that happen repeatedly are candidates for caching or algorithmic improvements.

**Common optimizations this reveals:**
- Replace Python loops with numpy/pandas operations
- Cache repeated computations or database queries
- Move expensive operations outside request handlers
- Use more efficient data structures
- Identify N+1 query patterns in database code

The goal isn't to optimize everything - focus on the lines that take significant time and are actually causing problems in production.

### Step 6: Clean Up (Optional)

When you're done profiling, swap the start commands back in `render.yaml`:

```yaml
startCommand: gunicorn app:app
# startCommand: scalene --cpu --html --profile-interval=15 --outfile=/tmp/scalene.html wrapper-app.py
```

Redeploy to remove the profiling overhead. Your service returns to normal operation.

## What You've Learned

You now know how to:
1. Deploy a Python web service to Render
2. Enable Scalene profiling with a simple config change
3. Generate realistic load for profiling
4. Download and interpret profiling reports
5. Identify CPU and memory bottlenecks in production code

The key insight: **profiling doesn't require code changes**. By using a wrapper script and Scalene's command-line interface, you can toggle profiling on and off just by changing your start command. This makes it easy to diagnose performance issues in any Python service running on Render.

## Adapting This for Your Application

The techniques in this guide work for any Python web service, not just Flask:

- **FastAPI/Starlette** - Create a wrapper that runs `uvicorn` with `workers=1` and `loop="asyncio"`
- **Django** - Use `gunicorn` with your Django WSGI app, same pattern as this example
- **Other ASGI apps** - Use `uvicorn` or `hypercorn` programmatically with single-worker config
- **Background workers** - Profile Celery workers, RQ workers, etc. with the same `scalene` wrapper approach

The wrapper pattern is universal: wrap your server startup in a Python script that configures it for single-process operation, then run that script under Scalene. Check out `wrapper-app.py` in this repo as a template and adapt it to your needs.

## License

MIT
