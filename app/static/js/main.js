// Smart Inventory Intelligence JS & Chart.js Controllers

document.addEventListener('DOMContentLoaded', function () {
    // 1. Seed Demo Data Button Handler
    const seedBtn = document.getElementById('btnSeedData');
    if (seedBtn) {
        seedBtn.addEventListener('click', function () {
            if (confirm("Reset database with realistic canteen products, suppliers & sales history?")) {
                seedBtn.disabled = true;
                seedBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Seeding...';
                
                fetch('/api/seed', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            alert("Database successfully seeded!");
                            window.location.reload();
                        } else {
                            alert("Error seeding data: " + data.message);
                            seedBtn.disabled = false;
                            seedBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise me-1"></i> Seed Demo Data';
                        }
                    })
                    .catch(err => {
                        alert("Failed to seed database.");
                        seedBtn.disabled = false;
                        seedBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise me-1"></i> Seed Demo Data';
                    });
            }
        });
    }

    // 2. Initialize Dashboard Charts if elements exist
    if (document.getElementById('chartSalesTrend')) {
        loadDashboardCharts();
    }
});

function loadDashboardCharts() {
    fetch('/api/charts/dashboard')
        .then(res => res.json())
        .then(data => {
            renderSalesTrendChart(data.sales_trend);
            renderCategoryChart(data.categories);
            renderStockVsDemandChart(data.stock_vs_demand);
            renderRiskDistributionChart(data.risk_summary);
        })
        .catch(err => console.error("Error loading dashboard charts:", err));
}

function renderSalesTrendChart(salesData) {
    const ctx = document.getElementById('chartSalesTrend').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: salesData.dates,
            datasets: [{
                label: 'Daily Revenue ($)',
                data: salesData.revenues,
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                fill: true,
                tension: 0.3,
                yAxisID: 'y'
            }, {
                label: 'Items Sold',
                data: salesData.quantities,
                borderColor: '#10b981',
                borderDash: [4, 4],
                tension: 0.3,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#495057' } }
            },
            scales: {
                x: { ticks: { color: '#495057' }, grid: { color: '#e9ecef' } },
                y: {
                    type: 'linear',
                    position: 'left',
                    ticks: { color: '#38bdf8' },
                    grid: { color: '#e9ecef' },
                    title: { display: true, text: 'Revenue ($)', color: '#38bdf8' }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    ticks: { color: '#10b981' },
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: 'Units Sold', color: '#10b981' }
                }
            }
        }
    });
}

function renderCategoryChart(catData) {
    const ctx = document.getElementById('chartCategory').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: catData.labels,
            datasets: [{
                data: catData.revenues,
                backgroundColor: ['#38bdf8', '#10b981', '#f59e0b', '#a855f7', '#f43f5e', '#64748b']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8' } }
            }
        }
    });
}

function renderStockVsDemandChart(stockData) {
    const ctx = document.getElementById('chartStockVsDemand').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: stockData.labels,
            datasets: [{
                label: 'Current Stock',
                data: stockData.current_stock,
                backgroundColor: '#38bdf8'
            }, {
                label: 'Predicted 7-Day Demand',
                data: stockData.predicted_demand,
                backgroundColor: '#f59e0b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#495057' } }
            },
            scales: {
                x: { ticks: { color: '#495057' }, grid: { color: '#e9ecef' } },
                y: { ticks: { color: '#495057' }, grid: { color: '#e9ecef' } }
            }
        }
    });
}

function renderRiskDistributionChart(riskData) {
    const ctx = document.getElementById('chartRiskSummary').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: riskData.labels,
            datasets: [{
                data: riskData.data,
                backgroundColor: ['#f43f5e', '#f59e0b', '#ef4444', '#fbbf24', '#10b981']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8' } }
            }
        }
    });
}
