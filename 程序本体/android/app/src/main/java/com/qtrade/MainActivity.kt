package com.qtrade

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.chaquo.python.Python

class MainActivity : AppCompatActivity() {
    private var _running = false
    private var _serviceIntent: Intent? = null
    private var _notifId = 0
    private var _notifBtn: View? = null
    private var _runningBtn: View? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 创建通知频道
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            createNotificationChannel()
        }

        val startBtn = findViewById<Button>(R.id.btnStart)
        val stopBtn = findViewById<Button>(R.id.btnStop)
        val statusText = findViewById<TextView>(R.id.statusText)
        _notifBtn = findViewById<View>(R.id.btnStart)
        _runningBtn = findViewById<View>(R.id.btnStop)

        startBtn.setOnClickListener { startTrading() }
        stopBtn.setOnClickListener { stopTrading() }

        // 默认启动状态
        statusText.text = "点击「启动」启动交易引擎（后台服务 + Python HTTP 服务器）"
        updateUI(false)
    }

    private fun startTrading() {
        if (_running) return
        _running = true

        // 启动前台服务
        val serviceIntent = Intent(this, TradingForegroundService::class.java)
        serviceIntent.putExtra("host", "0.0.0.0")
        serviceIntent.putExtra("port", 8000)
        serviceIntent.putExtra("token", intent?.getStringExtra("token") ?: "")
        startForegroundService(serviceIntent)

        // 启动 Python 服务器（后台线程）
        startPythonServer()

        // 通知
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(_notifId, buildNotification("交易引擎运行中"))

        statusText.text = "交易引擎已启动 — 实时查看 127.0.0.1:8000"
        updateUI(true)
    }

    private fun stopTrading() {
        _running = false
        if (_serviceIntent != null) {
            stopService(_serviceIntent)
            _serviceIntent = null
        }
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.cancel(_notifId)

        statusText.text = "交易引擎已停止"
        updateUI(false)
    }

    private fun startForegroundService(intent: Intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService()
        } else {
            startService(intent)
        }
    }

    private fun startPythonServer() {
        if (!Python.isSupported) {
            Toast.makeText(this, "Python 不可用", Toast.LENGTH_SHORT).show()
            return
        }
        val py = Python.getInstance()
        try {
            py.getModule("headless_server").callAttr("start_server",
                "0.0.0.0", 8000, intent?.getStringExtra("token")
            )
        } catch (e: Exception) {
            Toast.makeText(this, "Python 服务器启动失败: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun buildNotification(title: String): Notification {
        val pIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, "trading")
            .setContentTitle("AI 量化交易系统")
            .setContentText(title)
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setContentIntent(pIntent)
            .setOngoing(true)
            .build()
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            "trading",
            "交易引擎",
            NotificationManager.IMPORTANCE_LOW
        )
        channel.enableLights(true)
        channel.lightColor = android.R.color.holo_blue_light
        channel.enableVibration(true)
        channel.vibrationPattern = longArrayOf(100, 200, 100, 200)
        channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC)
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(channel)
    }

    private fun updateUI(running: Boolean) {
        startBtn.isEnabled = !running
        stopBtn.isEnabled = running
    }
}