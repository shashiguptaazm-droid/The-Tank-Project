import com.rankwarz.edulabsrtm.BaseActivity

// ... imports ...

data class QuestionModel(
    val id: Int,
    val question: String,
    val a: String, val b: String, val c: String, val d: String,
    val correctAnswer: String,
    val explanation: String,
    val imageUrl: String
)

