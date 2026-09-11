package com.rankwarz.edulabsrtm

import android.app.Activity
import android.content.Intent
import androidx.annotation.IdRes
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationBarView

fun AppCompatActivity.setupAppBottomNavigation(
    bottomNav: BottomNavigationView?,
    @IdRes selectedItemId: Int? = null
) {
    bottomNav ?: return
    AppBottomNavigation.setup(this, bottomNav, selectedItemId)
}

object AppBottomNavigation {
    fun setup(
        activity: Activity,
        bottomNav: BottomNavigationView,
        @IdRes selectedItemId: Int? = null
    ) {
        style(bottomNav)

        bottomNav.setOnItemSelectedListener(null)
        val resolvedSelection = selectedItemId ?: selectedItemIdFor(activity)
        if (resolvedSelection != 0 && bottomNav.menu.findItem(resolvedSelection) != null) {
            bottomNav.selectedItemId = resolvedSelection
        }

        bottomNav.setOnItemSelectedListener { item ->
            val target = targetActivityFor(item.itemId)
            when {
                target == null -> false
                activity::class.java == target -> true
                else -> {
                    activity.startActivity(
                        Intent(activity, target).apply {
                            addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                        }
                    )
                    activity.overridePendingTransition(0, 0)
                    true
                }
            }
        }
    }

    @IdRes
    fun selectedItemIdFor(activity: Activity): Int = when (activity) {
        is DashboardActivity,
        is TestSelectionActivity,
        is LobbyActivity,
        is TopicLobbyActivity,
        is ClassicGameActivity,
        is MCQActivity,
        is ProfileActivity,
        is LeaderboardActivity,
        is ChallengeResultActivity,
        is SettingsActivity,
        is GoalActivity,
        is EditProfileActivity,
        is ChallengeInvitationActivity,
        is CollegeDetailActivity,
        is LoadingActivity,
        is LoginActivity,
        is MainActivity,
        is MatchmakingActivity,
        is MatchmakingLoadingActivity,
        is NeetWidgetActivity,
        is QuestionAttemptsActivity,
        is QuizManagerActivity,
        is QuizViewerActivity,
        is ReferralActivity,
        is RegisterActivity,
        is ReviewActivity,
        is ScoresActivity,
        is SubjectTestActivity,
        is ThesisAnalyzerActivity,
        is TopicChallengeResultActivity,
        is TopicChallengeSelectionActivity,
        is TopicLoadingActivity,
        is TopicSelector,
        is VideoCallActivity,
        is WebViewActivity,
        is ExportThemeSelectionActivity,
        is FullScreenImageActivity,
        is SharedQuestionsActivity -> R.id.nav_home

        is AiChatActivity -> R.id.nav_reels
        is GlobalSearchActivity -> R.id.nav_search
        is ChallengeListActivity,
        is RecentChallengesActivity,
        is NewsFeedActivity,
        is PredictCollegeActivity,
        is AccuracyActivity -> R.id.nav_feed
        is MessengerActivity,
        is HelpActivity -> R.id.nav_messages
        is WidgetSettingsActivity -> R.id.nav_home
        else -> 0
    }

    private fun targetActivityFor(@IdRes itemId: Int): Class<out Activity>? = when (itemId) {
        R.id.nav_home -> DashboardActivity::class.java
        R.id.nav_reels -> AiChatActivity::class.java
        R.id.nav_search -> GlobalSearchActivity::class.java
        R.id.nav_feed -> ChallengeListActivity::class.java
        R.id.nav_messages -> MessengerActivity::class.java
        else -> null
    }

    private fun style(bottomNav: BottomNavigationView) {
        bottomNav.labelVisibilityMode = NavigationBarView.LABEL_VISIBILITY_LABELED
        bottomNav.isItemHorizontalTranslationEnabled = false
        bottomNav.itemIconTintList = ContextCompat.getColorStateList(bottomNav.context, R.color.bottom_nav_colors)
        bottomNav.itemTextColor = ContextCompat.getColorStateList(bottomNav.context, R.color.bottom_nav_colors)
        bottomNav.itemRippleColor = ContextCompat.getColorStateList(bottomNav.context, R.color.bottom_nav_ripple)
        bottomNav.setBackgroundColor(ContextCompat.getColor(bottomNav.context, R.color.colorSurface))
        bottomNav.elevation = bottomNav.resources.getDimension(R.dimen.bottom_nav_elevation)

        val initialBottomPadding = bottomNav.paddingBottom
        ViewCompat.setOnApplyWindowInsetsListener(bottomNav) { view, insets ->
            val navBars = insets.getInsets(WindowInsetsCompat.Type.navigationBars())
            view.updatePadding(bottom = initialBottomPadding + navBars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(bottomNav)
    }
}
