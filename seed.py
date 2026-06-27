from main import app, db
from models import User, Property, PropertyImage

with app.app_context():
    # امسح كل حاجة قديمة
    db.drop_all()
    db.create_all()
    
    # اعمل مستخدم تجريبي
    user = User(username='admin', email='admin@test.com', phone='01000000000')
    user.set_password('123456')
    db.session.add(user)
    db.session.commit()
    
    # ضيف 3 عقارات تجريبية
    p1 = Property(
        title='شقة سوبر لوكس في سموحة',
        description='شقة 3 غرف وريسبشن كبير',
        price=1500000,
        property_type='شقة',
        listing_type='بيع',
        location='سموحة، الإسكندرية',
        area=150,
        bedrooms=3,
        bathrooms=2,
        user_id=user.id
    )
    
    p2 = Property(
        title='فيلا بالتجمع الخامس',
        description='فيلا مستقلة بحديقة وحمام سباحة',
        price=8500000,
        property_type='فيلا',
        listing_type='بيع',
        location='التجمع الخامس، القاهرة',
        area=400,
        bedrooms=5,
        bathrooms=4,
        user_id=user.id
    )
    
    p3 = Property(
        title='محل للايجار في شارع فؤاد',
        description='محل تجاري موقع مميز',
        price=20000,
        property_type='محل',
        listing_type='إيجار',
        location='شارع فؤاد، الإسكندرية',
        area=80,
        user_id=user.id
    )
    
    db.session.add_all([p1, p2, p3])
    db.session.commit()
    
    # صور وهمية - لازم تحط صور حقيقية في static/properties/
    img1 = PropertyImage(filename='placeholder.jpg', property_id=p1.id, is_main=True)
    img2 = PropertyImage(filename='placeholder.jpg', property_id=p2.id, is_main=True)
    img3 = PropertyImage(filename='placeholder.jpg', property_id=p3.id, is_main=True)
    
    db.session.add_all([img1, img2, img3])
    db.session.commit()
    
    print("✓ تم إضافة 3 عقارات تجريبية")
    print("✓ ايميل: admin@test.com")
    print("✓ باسورد: 123456")