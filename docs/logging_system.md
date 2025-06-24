# Loglama Sistemi Dokümantasyonu

## 1. Genel Bakış

Projede üç ana loglama sistemi bulunmaktadır:

1. Güvenlik Logları (`security.log`)
2. Kullanıcı İşlem Logları (`user_operations.log`)
3. Veritabanı İşlem Logları (`database_operations.log`)

## 2. Log Dosyaları ve Konumları

### 2.1 Güvenlik Logları
**Dosya:** `logs/security.log`
**Sorumlu Sınıf:** `SecurityManager`

Bu log dosyası güvenlikle ilgili tüm olayları kaydeder:

| Log Seviyesi | Olay Tipi | Açıklama | Örnek Log Mesajı |
|--------------|-----------|-----------|------------------|
| INFO | TOKEN_VERIFIED | Başarılı token doğrulama | `2024-03-15 10:30:15 - INFO - TOKEN_VERIFIED: Token verified for user admin@example.com` |
| WARNING | TOKEN_EXPIRED | Süresi dolmuş token | `2024-03-15 10:35:20 - WARNING - TOKEN_EXPIRED: Token expired at 2024-03-15 10:30:15` |
| ERROR | TOKEN_ERROR | Token doğrulama hatası | `2024-03-15 10:40:25 - ERROR - TOKEN_ERROR: Token verification failed: Invalid signature` |
| INFO | ENCRYPTION | Dosya şifreleme işlemi | `2024-03-15 11:00:00 - INFO - ENCRYPTION: File encryption successful` |
| ERROR | DECRYPTION_ERROR | Şifre çözme hatası | `2024-03-15 11:05:00 - ERROR - DECRYPTION_ERROR: Decryption failed. Invalid password` |

### 2.2 Kullanıcı İşlem Logları
**Dosya:** `logs/user_operations.log`
**Sorumlu Sınıf:** `UserManager`

Kullanıcı yönetimi ile ilgili işlemleri kaydeder:

| Log Seviyesi | Olay Tipi | Açıklama | Örnek Log Mesajı |
|--------------|-----------|-----------|------------------|
| INFO | USER_CREATED | Yeni kullanıcı oluşturma | `2024-03-15 12:00:00 - INFO - USER_CREATED: New user created: user@example.com by admin@example.com` |
| INFO | USER_DELETED | Kullanıcı silme | `2024-03-15 12:30:00 - INFO - USER_DELETED: User user@example.com deleted by admin@example.com` |
| INFO | ROLE_CHANGED | Rol değişikliği | `2024-03-15 13:00:00 - INFO - ROLE_CHANGED: Role changed for user@example.com from user to moderator` |
| WARNING | LOGIN_ATTEMPT | Başarısız giriş denemesi | `2024-03-15 13:30:00 - WARNING - LOGIN_ATTEMPT: Failed login attempt for user@example.com` |
| ERROR | ACCOUNT_LOCKED | Hesap kilitleme | `2024-03-15 14:00:00 - ERROR - ACCOUNT_LOCKED: Account locked for user@example.com due to multiple failed attempts` |

### 2.3 Veritabanı İşlem Logları
**Dosya:** `logs/database_operations.log`
**Sorumlu Sınıf:** `DataManager`

Veritabanı işlemlerini kaydeder:

| Log Seviyesi | Olay Tipi | Açıklama | Örnek Log Mesajı |
|--------------|-----------|-----------|------------------|
| INFO | SCHEMA_UPDATED | Şema güncelleme | `2024-03-15 15:00:00 - INFO - SCHEMA_UPDATED: Database schema updated by admin@example.com` |
| INFO | DATA_MODIFIED | Veri değişikliği | `2024-03-15 15:30:00 - INFO - DATA_MODIFIED: Record #123 modified by user@example.com` |
| WARNING | CONCURRENT_ACCESS | Eşzamanlı erişim uyarısı | `2024-03-15 16:00:00 - WARNING - CONCURRENT_ACCESS: Multiple users attempting to modify same record` |
| ERROR | DATA_ERROR | Veri işleme hatası | `2024-03-15 16:30:00 - ERROR - DATA_ERROR: Failed to process Excel file: Invalid format` |

## 3. Log Seviyeleri ve Anlamları

### 3.1 INFO
- Normal sistem operasyonları
- Başarılı işlemler
- Rutin bilgilendirmeler

### 3.2 WARNING
- Potansiyel sorunlar
- Başarısız giriş denemeleri
- Süresi dolmuş tokenlar
- Performans uyarıları

### 3.3 ERROR
- Kritik hatalar
- Güvenlik ihlalleri
- Veri bütünlüğü sorunları
- Sistem hataları

## 4. Log Rotasyonu ve Yönetimi

### 4.1 Log Rotasyon Politikası
- Her log dosyası maksimum 10MB boyutunda olabilir
- Günlük rotasyon yapılır
- Son 30 günlük loglar saklanır
- Eski loglar sıkıştırılarak arşivlenir

### 4.2 Log Dosyası Formatı
```
TIMESTAMP - LEVEL - EVENT_TYPE: MESSAGE
```

Örnek:
```
2024-03-15 10:30:15 - INFO - USER_CREATED: New user created: user@example.com
```

## 5. Log İzleme ve Analiz

### 5.1 Güvenlik İzleme
- Başarısız giriş denemeleri
- Token kullanımı
- Şifreleme/şifre çözme işlemleri
- Yetki değişiklikleri

### 5.2 Performans İzleme
- Veritabanı işlem süreleri
- Eşzamanlı erişim sayıları
- Kaynak kullanımı
- Yanıt süreleri

### 5.3 Kullanıcı Aktivite İzleme
- Oturum açma/kapama
- Rol değişiklikleri
- Veri değişiklikleri
- Hesap yönetimi

## 6. Log Erişim Yetkileri

| Rol | Erişilebilir Loglar | İzinler |
|-----|---------------------|----------|
| Root | Tüm loglar | Okuma, Silme, Arşivleme |
| Admin | Kullanıcı ve DB Logları | Okuma |
| Moderator | Kendi işlem logları | Sadece Okuma |
| User | - | - |

## 7. Best Practices

1. **Log Güvenliği:**
   - Log dosyaları şifrelenmiş formatta saklanmalı
   - Hassas bilgiler maskelenmeli
   - Erişim yetkileri düzenli kontrol edilmeli

2. **Log Yönetimi:**
   - Düzenli yedekleme
   - Otomatik temizleme
   - Periyodik analiz

3. **Hata Ayıklama:**
   - Her hata için benzersiz kod
   - Detaylı hata açıklaması
   - Çözüm önerileri

## 8. Örnek Log Analizi Sorguları

```python
# Son 24 saatteki başarısız giriş denemeleri
grep "LOGIN_ATTEMPT" logs/user_operations.log | grep "$(date -d '24 hours ago' +'%Y-%m-%d')"

# Belirli bir kullanıcının tüm işlemleri
grep "user@example.com" logs/user_operations.log

# Kritik güvenlik olayları
grep "ERROR" logs/security.log
``` 