package com.rankwarz.edulabsrtm

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ValueAnimator
import android.app.Activity
import android.content.Context
import android.graphics.*
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.TextureView
import android.view.View
import android.view.ViewGroup
import android.view.animation.AccelerateDecelerateInterpolator
import kotlin.math.*
import kotlin.random.Random

/**
 * Cinematic "Entering the Matrix" 3D Transition & Screen Shatter Effect.
 * Shards the screen into digital fragments, plunges into the Matrix cyberspace with
 * 3D wireframe warp tunnel, cascading digital code rain, glitch scanlines, terminal HUD,
 * and rhythmic haptics before materializing the video again.
 */
class ScreenExplosionView(context: Context) : View(context) {

    companion object {
        private val MATRIX_GLYPHS = charArrayOf(
            'ｦ', 'ｱ', 'ｳ', 'ｴ', 'ｵ', 'ｶ', 'ｷ', 'ｹ', 'ｺ', 'ｻ', 'ｼ', 'ｽ', 'ｾ', 'ｿ',
            'ﾀ', 'ﾂ', 'ﾃ', 'ﾅ', 'ﾆ', 'ﾇ', 'ﾈ', 'ﾊ', 'ﾋ', 'ﾎ', 'ﾏ', 'ﾐ', 'ﾑ', 'ﾒ',
            'ﾓ', 'ﾔ', 'ﾕ', 'ﾗ', 'ﾘ', 'ﾜ', '0', '1', '2', '3', '5', '7', '8', '9',
            'A', 'B', 'C', 'D', 'E', 'F', 'X', 'Z', 'Ω', 'Ψ', '§', '¶', '0', '1'
        )
    }

    private var snapshotBitmap: Bitmap? = null
    private val shards = mutableListOf<Shard>()
    private val matrixColumns = mutableListOf<MatrixColumn>()

    private val shardPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val shardBorderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 2.5f
        color = Color.parseColor("#00FF41")
    }
    private val matrixHeadPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E0FFE8")
        typeface = Typeface.MONOSPACE
        isFakeBoldText = true
    }
    private val matrixBodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#00FF41")
        typeface = Typeface.MONOSPACE
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 1.5f
        color = Color.parseColor("#154820")
    }
    private val hudPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = Typeface.MONOSPACE
        isFakeBoldText = true
        textAlign = Paint.Align.CENTER
    }
    private val scanlinePaint = Paint().apply {
        color = Color.argb(45, 0, 255, 65)
        strokeWidth = 2f
    }
    private val flashPaint = Paint(Paint.ANTI_ALIAS_FLAG)

    private val camera3D = Camera()
    private val transformMatrix = Matrix()

    private var transitionProgress = 0f
    private var shakeOffsetX = 0f
    private var shakeOffsetY = 0f

    private var animator: ValueAnimator? = null
    private var onCompleteCallback: (() -> Unit)? = null
    private var onMidExplosionCallback: (() -> Unit)? = null
    private var midTriggered = false
    private var lastHapticTickTime = 0L

    private var hudTitle: String? = null
    private var hudSubtitle: String? = null
    private var hudFootnote: String? = null

    private val COLS = 12
    private val ROWS = 18

    data class Shard(
        val srcRect: Rect,
        val localDstRect: RectF,
        val origX: Float,
        val origY: Float,
        var currentX: Float,
        var currentY: Float,
        val vx: Float,
        val vy: Float,
        val rotSpeedX: Float,
        val rotSpeedY: Float,
        val rotSpeedZ: Float,
        var rotX: Float = 0f,
        var rotY: Float = 0f,
        var rotZ: Float = 0f,
        var scale: Float = 1f,
        var alpha: Float = 1f,
        val width: Float,
        val height: Float
    )

    data class MatrixColumn(
        val x: Float,
        var yHead: Float,
        val speed: Float,
        val length: Int,
        val charIndices: IntArray,
        val charSize: Float,
        val depthAlpha: Float
    )

    init {
        setWillNotDraw(false)
        isClickable = true
        isFocusable = false
    }

    fun startExplosion(
        bitmap: Bitmap?,
        hudTitle: String? = null,
        hudSubtitle: String? = null,
        hudFootnote: String? = null,
        onMidExplosion: (() -> Unit)? = null,
        onComplete: () -> Unit
    ) {
        this.snapshotBitmap = bitmap
        this.hudTitle = hudTitle
        this.hudSubtitle = hudSubtitle
        this.hudFootnote = hudFootnote
        this.onMidExplosionCallback = onMidExplosion
        this.onCompleteCallback = onComplete
        this.midTriggered = false

        post {
            initShards()
            initMatrixRain()
            triggerHapticBurst()
            runAnimation()
        }
    }

    private fun initShards() {
        shards.clear()

        val viewW = width.toFloat().coerceAtLeast(100f)
        val viewH = height.toFloat().coerceAtLeast(100f)
        val epicX = viewW / 2f
        val epicY = viewH / 2f
        val maxDist = hypot(viewW, viewH) / 1.4f

        val bmpW = snapshotBitmap?.width?.toFloat() ?: viewW
        val bmpH = snapshotBitmap?.height?.toFloat() ?: viewH

        val cellW = viewW / COLS
        val cellH = viewH / ROWS
        val srcCellW = bmpW / COLS
        val srcCellH = bmpH / ROWS

        for (r in 0 until ROWS) {
            for (c in 0 until COLS) {
                val origX = c * cellW + cellW / 2f
                val origY = r * cellH + cellH / 2f

                val dx = origX - epicX
                val dy = origY - epicY
                var angle = atan2(dy, dx)
                angle += (Random.nextFloat() - 0.5f) * 0.4f

                val dist = hypot(dx, dy)
                val baseSpeed = 1200f + Random.nextFloat() * 1500f
                val speedMultiplier = (1.2f - (dist / maxDist) * 0.4f).coerceIn(0.7f, 1.4f)
                val speed = baseSpeed * speedMultiplier

                val vx = cos(angle) * speed
                val vy = sin(angle) * speed - (250f + Random.nextFloat() * 300f)

                val srcLeft = (c * srcCellW).toInt()
                val srcTop = (r * srcCellH).toInt()
                val srcRight = ((c + 1) * srcCellW).toInt().coerceAtMost(bmpW.toInt())
                val srcBottom = ((r + 1) * srcCellH).toInt().coerceAtMost(bmpH.toInt())

                shards.add(
                    Shard(
                        srcRect = Rect(srcLeft, srcTop, srcRight, srcBottom),
                        localDstRect = RectF(-cellW / 2f, -cellH / 2f, cellW / 2f, cellH / 2f),
                        origX = origX,
                        origY = origY,
                        currentX = origX,
                        currentY = origY,
                        vx = vx,
                        vy = vy,
                        rotSpeedX = (Random.nextFloat() - 0.5f) * 800f,
                        rotSpeedY = (Random.nextFloat() - 0.5f) * 800f,
                        rotSpeedZ = (Random.nextFloat() - 0.5f) * 500f,
                        width = cellW,
                        height = cellH
                    )
                )
            }
        }
    }

    private fun initMatrixRain() {
        matrixColumns.clear()
        val viewW = width.toFloat().coerceAtLeast(100f)
        val viewH = height.toFloat().coerceAtLeast(100f)

        val columnSpacing = 28f
        val numColumns = (viewW / columnSpacing).toInt() + 2

        for (i in 0 until numColumns) {
            val colX = i * columnSpacing
            val len = Random.nextInt(14, 28)
            val chars = IntArray(len) { Random.nextInt(MATRIX_GLYPHS.size) }
            val charSize = 22f + Random.nextFloat() * 10f
            val speed = 800f + Random.nextFloat() * 1400f
            val startY = -Random.nextFloat() * viewH * 0.8f

            matrixColumns.add(
                MatrixColumn(
                    x = colX,
                    yHead = startY,
                    speed = speed,
                    length = len,
                    charIndices = chars,
                    charSize = charSize,
                    depthAlpha = 0.5f + Random.nextFloat() * 0.5f
                )
            )
        }
    }

    private fun triggerHapticBurst() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
                vm?.defaultVibrator?.vibrate(
                    VibrationEffect.createPredefined(VibrationEffect.EFFECT_HEAVY_CLICK)
                )
            } else {
                @Suppress("DEPRECATION")
                val v = context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    v?.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
                } else {
                    @Suppress("DEPRECATION")
                    v?.vibrate(100)
                }
            }
        } catch (_: Exception) {}
    }

    private fun triggerMicroHaptic() {
        val now = System.currentTimeMillis()
        if (now - lastHapticTickTime < 180) return
        lastHapticTickTime = now
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val v = context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
                v?.vibrate(VibrationEffect.createPredefined(VibrationEffect.EFFECT_TICK))
            }
        } catch (_: Exception) {}
    }

    private fun runAnimation() {
        animator?.cancel()
        animator = ValueAnimator.ofFloat(0f, 1f).apply {
            duration = 2800L
            interpolator = AccelerateDecelerateInterpolator()
            addUpdateListener { va ->
                val p = va.animatedValue as Float
                transitionProgress = p

                if (p < 0.18f) {
                    val decay = 1f - (p / 0.18f)
                    shakeOffsetX = (Random.nextFloat() - 0.5f) * 22f * decay
                    shakeOffsetY = (Random.nextFloat() - 0.5f) * 22f * decay
                } else {
                    shakeOffsetX = 0f
                    shakeOffsetY = 0f
                }

                val shatterDt = (p / 0.35f).coerceAtMost(1f) * 0.7f
                val gravity = 1800f
                for (shard in shards) {
                    shard.currentX = shard.origX + shard.vx * shatterDt
                    shard.currentY = shard.origY + shard.vy * shatterDt + 0.5f * gravity * shatterDt * shatterDt
                    shard.rotX = shard.rotSpeedX * shatterDt
                    shard.rotY = shard.rotSpeedY * shatterDt
                    shard.rotZ = shard.rotSpeedZ * shatterDt
                    shard.scale = (1f - p * 1.5f).coerceAtLeast(0.05f)
                    shard.alpha = (1f - (p / 0.28f)).coerceIn(0f, 1f)
                }

                if (p > 0.08f) {
                    val warpMultiplier = if (p > 0.75f) 1f + (p - 0.75f) * 6f else 1f
                    for (col in matrixColumns) {
                        col.yHead += col.speed * 0.016f * warpMultiplier
                        if (col.yHead > height + col.length * col.charSize) {
                            col.yHead = -col.length * col.charSize
                        }
                        if (Random.nextFloat() < 0.08f) {
                            val rIdx = Random.nextInt(col.charIndices.size)
                            col.charIndices[rIdx] = Random.nextInt(MATRIX_GLYPHS.size)
                        }
                    }
                    if (p in 0.20f..0.80f) {
                        triggerMicroHaptic()
                    }
                }

                if (p >= 0.65f && !midTriggered) {
                    midTriggered = true
                    onMidExplosionCallback?.invoke()
                }

                invalidate()
            }

            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    cleanUp()
                    onCompleteCallback?.invoke()
                }
            })
            start()
        }
    }

    private fun cleanUp() {
        snapshotBitmap?.recycle()
        snapshotBitmap = null
        shards.clear()
        matrixColumns.clear()
        (parent as? ViewGroup)?.removeView(this)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val w = width.toFloat()
        val h = height.toFloat()
        val p = transitionProgress

        canvas.save()
        canvas.translate(shakeOffsetX, shakeOffsetY)

        // 1. Matrix background
        val bgAlpha = when {
            p < 0.12f -> (p / 0.12f) * 245f
            p > 0.88f -> ((1f - p) / 0.12f) * 245f
            else -> 245f
        }
        canvas.drawColor(Color.argb(bgAlpha.toInt().coerceIn(0, 255), 2, 8, 3))

        // 2. 3D Wireframe Warp Tunnel
        if (p in 0.10f..0.92f) {
            val tunnelAlpha = when {
                p < 0.25f -> (p - 0.10f) / 0.15f
                p > 0.82f -> (0.92f - p) / 0.10f
                else -> 1f
            }
            gridPaint.alpha = (tunnelAlpha * 90).toInt().coerceIn(0, 255)
            val cx = w / 2f
            val cy = h / 2f

            val numRays = 16
            for (i in 0 until numRays) {
                val angle = i * (2f * Math.PI.toFloat() / numRays)
                val rayLen = hypot(w, h)
                val rx = cx + cos(angle) * rayLen
                val ry = cy + sin(angle) * rayLen
                canvas.drawLine(cx, cy, rx, ry, gridPaint)
            }

            val speedOffset = (p * 5f) % 1f
            for (ring in 1..7) {
                val ringP = ((ring + speedOffset) / 8f).pow(2.2f)
                val ringW = w * ringP * 1.3f
                val ringH = h * ringP * 1.3f
                gridPaint.alpha = (tunnelAlpha * (100 * ringP)).toInt().coerceIn(0, 255)
                canvas.drawRect(cx - ringW / 2f, cy - ringH / 2f, cx + ringW / 2f, cy + ringH / 2f, gridPaint)
            }
        }

        // 3. Digital Code Rain
        if (p > 0.08f) {
            val rainAlpha = when {
                p < 0.22f -> (p - 0.08f) / 0.14f
                p > 0.85f -> (1f - p) / 0.15f
                else -> 1f
            }

            for (col in matrixColumns) {
                matrixHeadPaint.textSize = col.charSize
                matrixBodyPaint.textSize = col.charSize

                for (i in 0 until col.length) {
                    val glyphY = col.yHead - i * (col.charSize * 1.15f)
                    if (glyphY < -50 || glyphY > h + 50) continue

                    val glyph = MATRIX_GLYPHS[col.charIndices[i % col.charIndices.size]]

                    if (i == 0) {
                        matrixHeadPaint.alpha = (rainAlpha * 255).toInt().coerceIn(0, 255)
                        canvas.drawText(glyph.toString(), col.x, glyphY, matrixHeadPaint)
                    } else {
                        val trailFade = (1f - (i.toFloat() / col.length.toFloat())).pow(1.3f)
                        val glyphAlpha = (rainAlpha * col.depthAlpha * trailFade * 230).toInt().coerceIn(0, 255)
                        matrixBodyPaint.alpha = glyphAlpha
                        if (i < 3) {
                            matrixBodyPaint.color = Color.parseColor("#43FF75")
                        } else {
                            matrixBodyPaint.color = Color.parseColor("#00FF41")
                        }
                        canvas.drawText(glyph.toString(), col.x, glyphY, matrixBodyPaint)
                    }
                }
            }
        }

        // 4. Matrix Terminal HUD (Only displayed when hudTitle is non-null, e.g. at login/splash)
        if (!hudTitle.isNullOrBlank() && p in 0.18f..0.85f) {
            val hudAlpha = when {
                p < 0.30f -> (p - 0.18f) / 0.12f
                p > 0.78f -> (0.85f - p) / 0.07f
                else -> 1f
            }

            val line1 = hudSubtitle ?: "> SYSTEM OVERRIDE: NEURAL LINK ACTIVE"
            val line2 = hudTitle ?: ""
            val cursor = if ((System.currentTimeMillis() / 250) % 2L == 0L) " █" else ""

            hudPaint.textSize = 20f
            hudPaint.color = Color.parseColor("#76FF9D")
            hudPaint.alpha = (hudAlpha * 240).toInt().coerceIn(0, 255)
            canvas.drawText(line1, w / 2f, h * 0.44f, hudPaint)

            hudPaint.textSize = 32f
            hudPaint.color = Color.parseColor("#E0FFE8")
            hudPaint.alpha = (hudAlpha * 255).toInt().coerceIn(0, 255)
            canvas.drawText(line2 + cursor, w / 2f, h * 0.50f, hudPaint)

            if (!hudFootnote.isNullOrBlank()) {
                hudPaint.textSize = 18f
                hudPaint.color = Color.parseColor("#00FF41")
                hudPaint.alpha = (hudAlpha * 220).toInt().coerceIn(0, 255)
                val progressPercent = ((p - 0.18f) / 0.67f * 100).toInt().coerceIn(0, 100)
                canvas.drawText("$hudFootnote: $progressPercent%", w / 2f, h * 0.55f, hudPaint)
            }
        }

        // 5. 3D Shards (Phase 1)
        if (p < 0.32f) {
            val bmp = snapshotBitmap
            for (shard in shards) {
                if (shard.alpha <= 0.02f) continue

                camera3D.save()
                camera3D.rotateX(shard.rotX)
                camera3D.rotateY(shard.rotY)
                camera3D.rotateZ(shard.rotZ)
                camera3D.getMatrix(transformMatrix)
                camera3D.restore()

                transformMatrix.preTranslate(-shard.width / 2f, -shard.height / 2f)
                transformMatrix.postScale(shard.scale, shard.scale)
                transformMatrix.postTranslate(shard.currentX, shard.currentY)

                canvas.save()
                canvas.concat(transformMatrix)

                shardPaint.alpha = (shard.alpha * 255).toInt()
                if (bmp != null && !bmp.isRecycled) {
                    canvas.drawBitmap(bmp, shard.srcRect, shard.localDstRect, shardPaint)
                } else {
                    shardPaint.color = Color.argb((shard.alpha * 200).toInt(), 0, 40, 15)
                    canvas.drawRoundRect(shard.localDstRect, 6f, 6f, shardPaint)
                }

                shardBorderPaint.alpha = (shard.alpha * 220).toInt()
                canvas.drawRoundRect(shard.localDstRect, 3f, 3f, shardBorderPaint)

                canvas.restore()
            }
        }

        // 6. Scanlines
        if (p in 0.05f..0.88f) {
            val scanOffset = (p * 2000f) % 24f
            var yScan = scanOffset
            while (yScan < h) {
                canvas.drawLine(0f, yScan, w, yScan, scanlinePaint)
                yScan += 18f
            }
        }

        // 7. Warp Flash
        if (p > 0.82f) {
            val flashP = (p - 0.82f) / 0.18f
            val flashAlpha = if (flashP < 0.45f) {
                (flashP / 0.45f) * 190f
            } else {
                ((1f - flashP) / 0.55f) * 190f
            }
            flashPaint.color = Color.argb(flashAlpha.toInt().coerceIn(0, 255), 0, 255, 65)
            canvas.drawRect(0f, 0f, w, h, flashPaint)
        }

        canvas.restore()
    }
}

/**
 * Static Utility to trigger the Matrix transition on any Activity or View.
 */
object ScreenExplosionHelper {

    fun triggerExplosion(
        activity: Activity,
        textureView: TextureView? = null,
        hudTitle: String? = null,
        hudSubtitle: String? = null,
        hudFootnote: String? = null,
        onMidExplosion: (() -> Unit)? = null,
        onComplete: () -> Unit
    ) {
        activity.runOnUiThread {
            try {
                val decorView = activity.window.decorView as? ViewGroup ?: run {
                    onComplete()
                    return@runOnUiThread
                }

                val width = (decorView.width / 2).coerceAtLeast(360)
                val height = (decorView.height / 2).coerceAtLeast(640)

                val snapshot: Bitmap? = try {
                    if (textureView != null && textureView.isAvailable) {
                        val videoBmp = textureView.getBitmap(width, height)
                        val combined = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                        val c = Canvas(combined)
                        if (videoBmp != null) {
                            c.drawBitmap(videoBmp, 0f, 0f, null)
                        }
                        decorView.draw(c)
                        combined
                    } else {
                        val combined = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                        val c = Canvas(combined)
                        decorView.draw(c)
                        combined
                    }
                } catch (_: Exception) {
                    null
                }

                val explosionView = ScreenExplosionView(activity).apply {
                    layoutParams = ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                    )
                }

                decorView.addView(explosionView)
                explosionView.bringToFront()

                explosionView.startExplosion(
                    bitmap = snapshot,
                    hudTitle = hudTitle,
                    hudSubtitle = hudSubtitle,
                    hudFootnote = hudFootnote,
                    onMidExplosion = onMidExplosion,
                    onComplete = onComplete
                )
            } catch (e: Exception) {
                onComplete()
            }
        }
    }
}
