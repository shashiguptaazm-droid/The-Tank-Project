package com.rankwarz.edulabsrtm

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationView

abstract class BaseActivity : AppCompatActivity() {

    // Shared invite state across screens
    protected val acceptedInvites = mutableSetOf<String>()
    protected val shownInvites = mutableSetOf<String>()

    // Global FCM invite receiver
    private val inviteReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val lobbyId = intent?.getStringExtra("lobby_id") ?: return

            // Prevent duplicate popup
            if (acceptedInvites.contains(lobbyId) || shownInvites.contains(lobbyId)) return

            val timestamp = intent.getStringExtra("timestamp")?.toLongOrNull() ?: 0L
            val now = System.currentTimeMillis()

            // Ignore if invite is older than 5 minutes
            if (timestamp <= 0L || now - timestamp > 5 * 60 * 1000L) return

            val host = intent.getStringExtra("host_name") ?: "Friend"
            shownInvites.add(lobbyId)

            showGlobalInvite(host, lobbyId, intent)
        }
    }


    override fun onPause() {
        super.onPause()
        try {
            unregisterReceiver(inviteReceiver)
        } catch (_: Exception) {
            // ignore if already unregistered
        }
    }

    // Default invite UI fallback; override in DashboardActivity for banner UI
    open fun showGlobalInvite(host: String, lobbyId: String, data: Intent) {
        Toast.makeText(this, "⚔️ $host invited you!", Toast.LENGTH_LONG).show()
    }

    // Shared logic for both Bottom Nav and Side Nav
    protected fun setupNavigation(
        drawerLayout: DrawerLayout,
        bottomNav: BottomNavigationView,
        sideNav: NavigationView
    ) {
        setupAppBottomNavigation(bottomNav)

        sideNav.setNavigationItemSelectedListener { item ->
            drawerLayout.closeDrawer(GravityCompat.START)
            handleNavigation(item.itemId)
        }
    }

    private fun handleNavigation(itemId: Int): Boolean {
        val currentActivity = this::class.java

        val targetActivity = when (itemId) {
            R.id.nav_home -> DashboardActivity::class.java
            R.id.nav_messages -> MessengerActivity::class.java
            R.id.nav_feed -> ChallengeListActivity::class.java
            R.id.nav_reels -> AiChatActivity::class.java
            R.id.nav_search -> GlobalSearchActivity::class.java
            else -> null
        }

        return if (targetActivity != null && currentActivity != targetActivity) {
            val intent = Intent(this, targetActivity)
            intent.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
            startActivity(intent)
            true
        } else {
            false
        }
    }
}
