from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)


app.secret_key = '123'


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(30), unique=True, nullable=False)

    results = db.relationship('Result', backref='user', lazy=True)


class Level(db.Model):
    __tablename__ = 'levels'
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.Text, nullable=False)

    results = db.relationship('Result', backref='level', lazy=True)


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    level_id = db.Column(db.Integer, db.ForeignKey('levels.id'), nullable=False)
    speed = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    incorrect = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    

@app.route('/')
def index():
    # если ключа user_id (название сами придумываем) нет в сессиях
    # значит пользователь не залогинился, значит отображаем страницу index.html
    if 'user_id' not in session:
        return render_template('index.html', sessionId=session.get('user_id', None), user_in_sess=False)
    # если ключ user_id есть в сессиях
    # значит пользователь залогинился, значит отображаем страницу profile.html
    # и передаём в неё пользователя с id, равным значению, который лежит по ключу user_id в сессии
    else:
        user = User.query.filter_by(id=session.get('user_id')).first()
        return render_template('index.html', par=user, sessionId=session.get('user_id', None), user_in_sess=True)
    #return render_template('index.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    else:
        return render_template('register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # ищем в таблице User пользователя с почтой и паролем, который мы ввели в форму
        user = User.query.filter_by(email=email, password=password).first()
        # если такой пользователь есть
        if user:
            # создаём ключ user_id (название для ключа любое) и присваиваем ему значение,
            # равное id найденного пользователя
            session['user_id'] = user.id
            # отображаем страницу пользователя и передаём туда пользователя, который вошел в систему
            return render_template('profile.html', par=user)
        # если пользователя с такими данными нет - тогда перенаправление на страницу логина снова
        else:
            return redirect('/login')
    else:
        return render_template('login.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')  # перенаправляем на страницу входа, если пользователь не авторизован
    user = User.query.filter_by(id=session['user_id']).first()
    return render_template('profile.html', par=user)


# функция кнопки выхода из системы на страницу profile.html - удаляет значение по ключу user_id
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect('/')


@app.route('/levels_page')
def levels_page():
    if 'user_id' not in session:
        return render_template('index.html', sessionId=session.get('user_id', None), user_in_sess=False)
    # если ключ user_id есть в сессиях
    # значит пользователь залогинился, значит отображаем страницу profile.html
    # и передаём в неё пользователя с id, равным значению, который лежит по ключу user_id в сессии
    else:
        return render_template("levels_page.html")


@app.route('/get_level/<int:level_id>')
def get_level(level_id):
    level = Level.query.get(level_id)
    if level and ('user_id' in session):
        return render_template('index.html', sentence=level.sentence, level_id=level.id, sessionId=session.get('user_id', None), user_in_sess=True)
    else:
        return redirect('index', user_in_sess=False)
    

@app.route('/save_results', methods=['POST'])
def save_results():
    data = request.get_json()

    new_result = Result(
        user_id=session.get('user_id'),   # вот здесь исправил, было просто user_id = 1
        level_id=data['id_level'],
        speed=data['speed'],
        accuracy=data['accuracy'],
        correct=data['correct_text'],
        incorrect=data['incorrect_text']
    )

    db.session.add(new_result)
    db.session.commit()

    return jsonify({'success': True})


@app.route('/get_best_result/<int:level_id>')
def get_best_result(level_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Вы не вошли в систему'}), 403

    user_id = session['user_id']

    # Лучший результат текущего пользователя
    user_best_result = Result.query.filter_by(user_id=user_id, level_id=level_id).order_by(Result.speed.desc()).first()

    if user_best_result:
        user_result_data = {
            'speed': user_best_result.speed,
            'accuracy': user_best_result.accuracy,
            'correct': user_best_result.correct,
            'incorrect': user_best_result.incorrect,
            'date': user_best_result.date.strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        user_result_data = None

    # Лучший результат среди всех пользователей
    best_result = Result.query.filter_by(level_id=level_id).order_by(Result.speed.desc()).first()

    if best_result:
        best_user = User.query.get(best_result.user_id)
        best_result_data = {
            'speed': best_result.speed,
            'accuracy': best_result.accuracy,
            'correct': best_result.correct,
            'incorrect': best_result.incorrect,
            'date': best_result.date.strftime('%Y-%m-%d %H:%M:%S'),
            'username': best_user.username
        }
    else:
        best_result_data = None

    return jsonify({'user_best_result': user_result_data, 'best_result': best_result_data})


if __name__ == '__main__':
    
    sentences = [
            "Сегодняшний день был настолько жарким, что даже птицы не пели. Небо окрасилось в золотистые тона.",
            "После дождя на асфальте остались блестящие отражения. Летний дождь быстро закончился.",
            "Лучи солнца проникали сквозь листву деревьев, создавая игру света и тени. Солнце освещало лес своими последними лучами.",
            "В воздухе пахло свежей зеленью и цветами. Звуки природы создавали гармонию.",
            "По дороге встретилась стая птиц, мирно клюющих зерно. Поля были покрыты цветущими маками.",
            "Ветер шептал секреты старых деревьев, покачивая их кроны. Далеко на горизонте виднелись горы.",
            "Вдали виднелись горы, покрытые пышными зелеными лесами. На полянке цвели дикие цветы.",
            "Ручей медленно тек вдоль дороги, создавая успокаивающий звук. Сосны тянулись к небу.",
            "Мы сидели на берегу озера и наблюдали за игрой света на водной глади. Туман окутывал долину.",
            "Каждый шаг наполнял наши легкие свежим воздухом и чистотой природы. В лесу пахло хвоей и свежестью.",
            "Летний день расцвел во всей своей красе, словно картина художника. Ночь была тихой и спокойной.",
            "Лес зашумел, когда мы прошли мимо его таинственных глубин. Лесной пруд отражал звездное небо.",
            "Вода в реке блестела на солнце, словно тысячи бриллиантов. Дорога вела нас вглубь зелёного леса.",
            "Птицы чирикали в кустах, напевая мелодии радости и свободы. Вдалеке слышался шум водопада.",
            "Закатное небо окрасилось в огненные оттенки, создавая волшебное зрелище. Звуки леса становились громче с наступлением ночи.",
            "Вдали зазвучали звуки флейты, приглашая нас в мир музыки и мечтаний. Птицы возвращались в свои гнезда, завершив дневные хлопоты.",
            "Лепестки цветов падали на землю, словно красочный ковер. Вечерний бриз приносил свежесть и прохладу.",
            "Мы пересекли поля, покрытые золотистой травой, идущей до горизонта. Мы пересекли мост, ведущий в сказочный лес.",
            "Воздух наполнился ароматом свежих ягод, растущих в лесу. Светлячки порхали над лугом, создавая волшебную атмосферу.",
            "Звезды зажглись на ночном небе, как мерцающие алмазы. Звезды сверкали на ночном небе, словно драгоценные камни в чёрном бархате.",
            "В лесу слышался шепот листьев под ногами, словно приглашение на таинственное путешествие. Мы собрались у костра, обогреваясь его теплом и слушая шепот огня.",
            "Роса украсила траву мелкими алмазами, блестящими на солнце. Солнце медленно скрывалось за горизонтом, окрашивая небо в оранжевые и розовые тона.",
            "Паутина покрывала ветви деревьев, словно тонкие нити хрустального кружева. Дождевые капли тихо стучали по листьям, создавая музыку дождя.",
            "Звуки природы наполнили наши сердца радостью и умиротворением. Воздух был пронизан ароматами цветов и трав, создавая неповторимый букет.",
            "Луна взошла над горизонтом, освещая ночной лес своим мягким светом. Прогулка под лунным светом вечером вдохновляет на мечтания и размышления."
        ]

    with app.app_context():
        # создание базы данных
        db.create_all()

        # проверяем, есть ли в таблице записи, если нет - тогда только добавляем
        if Level.query.count() == 0:
            for sentence in sentences:
                new_level = Level(sentence=sentence)
                db.session.add(new_level)

            db.session.commit()
    # старт сервера, port=0 значит любой свободный порт
    app.run(debug=True, port=0)
