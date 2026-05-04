from flask import Flask, render_template_string, jsonify
import threading
import asyncio
from handlers.dashboard_handler import (
    get_message_stats,
    get_keyword_tags,
    get_important_messages,
    generate_weekly_activity_report
)

app = Flask(__name__)

# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Bot Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .important-messages { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .message-item { border-bottom: 1px solid #eee; padding: 10px 0; }
        .keyword-tags { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tag-item { display: inline-block; background: #e3f2fd; padding: 5px 10px; margin: 5px; border-radius: 4px; }
        h1, h2 { color: #333; }
        .refresh-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-bottom: 20px; }
        .refresh-btn:hover { background: #1976D2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Telegram Bot Dashboard</h1>
            <button class="refresh-btn" onclick="location.reload()">새로고침</button>
        </div>

        <div class="stats-grid" id="stats-grid">
            <!-- Stats will be loaded here -->
        </div>

        <div class="chart-container">
            <h2>📈 일일 메시지 통계</h2>
            <canvas id="dailyChart"></canvas>
        </div>

        <div class="chart-container">
            <h2>🕐 시간별 메시지 통계</h2>
            <canvas id="hourlyChart"></canvas>
        </div>

        <div class="chart-container">
            <h2>👥 사용자별 활동</h2>
            <canvas id="userChart"></canvas>
        </div>

        <div class="keyword-tags">
            <h2>🏷️ 키워드 태그 설정</h2>
            <div id="keyword-tags">
                <!-- Tags will be loaded here -->
            </div>
        </div>

        <div class="important-messages">
            <h2>⚠️ 중요 메시지</h2>
            <div id="important-messages">
                <!-- Important messages will be loaded here -->
            </div>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                const [statsResponse, tagsResponse, importantResponse, activityResponse] = await Promise.all([
                    fetch('/api/stats'),
                    fetch('/api/tags'),
                    fetch('/api/important'),
                    fetch('/api/activity')
                ]);

                const stats = await statsResponse.json();
                const tags = await tagsResponse.json();
                const important = await importantResponse.json();
                const activity = await activityResponse.json();

                updateStats(stats);
                updateCharts(stats, activity);
                updateTags(tags);
                updateImportantMessages(important);
            } catch (error) {
                console.error('데이터 로드 오류:', error);
            }
        }

        function updateStats(stats) {
            const grid = document.getElementById('stats-grid');
            const totalMessages = Object.values(stats.daily).reduce((a, b) => a + b, 0);
            const totalUsers = stats.top_users.length;
            const totalTopics = Object.keys(stats.topics).length;

            grid.innerHTML = `
                <div class="stat-card">
                    <h3>💬 총 메시지</h3>
                    <p style="font-size: 2em; color: #2196F3;">${totalMessages}</p>
                    <p>최근 7일</p>
                </div>
                <div class="stat-card">
                    <h3>👥 활성 사용자</h3>
                    <p style="font-size: 2em; color: #4CAF50;">${totalUsers}</p>
                    <p>상위 10명</p>
                </div>
                <div class="stat-card">
                    <h3>📂 토픽 수</h3>
                    <p style="font-size: 2em; color: #FF9800;">${totalTopics}</p>
                    <p>활성 토픽</p>
                </div>
            `;
        }

        function updateCharts(stats, activity) {
            // Daily chart
            const dailyCtx = document.getElementById('dailyChart').getContext('2d');
            new Chart(dailyCtx, {
                type: 'line',
                data: {
                    labels: Object.keys(stats.daily),
                    datasets: [{
                        label: '메시지 수',
                        data: Object.values(stats.daily),
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // Hourly chart
            const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
            new Chart(hourlyCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(stats.hourly).map(h => `${h}시`),
                    datasets: [{
                        label: '메시지 수',
                        data: Object.values(stats.hourly),
                        backgroundColor: '#4CAF50'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            // User chart
            const userCtx = document.getElementById('userChart').getContext('2d');
            new Chart(userCtx, {
                type: 'doughnut',
                data: {
                    labels: stats.top_users.map(u => u.name),
                    datasets: [{
                        data: stats.top_users.map(u => u.count),
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                            '#4BC0C0', '#FF6384'
                        ]
                    }]
                },
                options: {
                    responsive: true
                }
            });
        }

        function updateTags(tags) {
            const container = document.getElementById('keyword-tags');
            container.innerHTML = Object.entries(tags).map(([keyword, info]) => `
                <span class="tag-item" style="background-color: ${getColorCode(info.color)}">
                    ${keyword} → ${info.forward_topic || '태그만'}
                </span>
            `).join('');
        }

        function updateImportantMessages(messages) {
            const container = document.getElementById('important-messages');
            container.innerHTML = messages.map(msg => `
                <div class="message-item">
                    <strong>${msg.user_name}</strong> (${new Date(msg.timestamp).toLocaleString()}):
                    <p>${msg.text}</p>
                </div>
            `).join('');
        }

        function getColorCode(color) {
            const colors = {
                'red': '#ffebee',
                'green': '#e8f5e8',
                'blue': '#e3f2fd',
                'yellow': '#fffde7'
            };
            return colors[color] || '#f5f5f5';
        }

        // Load data on page load
        loadData();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/stats')
def get_stats():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        stats = loop.run_until_complete(get_message_stats())
        return jsonify(stats)
    finally:
        loop.close()

@app.route('/api/tags')
def get_tags():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        tags = loop.run_until_complete(get_keyword_tags())
        return jsonify(tags)
    finally:
        loop.close()

@app.route('/api/important')
def get_important():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        messages = loop.run_until_complete(get_important_messages())
        return jsonify(messages)
    finally:
        loop.close()

@app.route('/api/activity')
def get_activity():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        activity = loop.run_until_complete(generate_weekly_activity_report())
        return jsonify(activity)
    finally:
        loop.close()

def start_dashboard_server(port=5000):
    """Start the Flask dashboard server in a separate thread"""
    def run_app():
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run_app, daemon=True)
    thread.start()
    print(f"📊 대시보드 서버가 http://localhost:{port}에서 실행 중입니다.")