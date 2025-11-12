const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

// AmÃ©lioration de l'animation avec des transitions plus fluides
function toggleForm(isRegister) {
    if (!container) return;
    
    // Animation fluide
    container.style.transition = 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
    
    if (isRegister) {
        container.classList.add('active');
        // Animation des inputs
        const registerInputs = document.querySelectorAll('.register input');
        registerInputs.forEach((input, index) => {
            input.style.opacity = '0';
            input.style.transform = 'translateY(20px)';
            setTimeout(() => {
                input.style.transition = 'all 0.4s ease';
                input.style.opacity = '1';
                input.style.transform = 'translateY(0)';
            }, 200 + (index * 50));
        });
    } else {
        container.classList.remove('active');
        // Animation des inputs
        const loginInputs = document.querySelectorAll('.login input');
        loginInputs.forEach((input, index) => {
            input.style.opacity = '0';
            input.style.transform = 'translateY(20px)';
            setTimeout(() => {
                input.style.transition = 'all 0.4s ease';
                input.style.opacity = '1';
                input.style.transform = 'translateY(0)';
            }, 200 + (index * 50));
        });
    }
}

// VÃ©rifier si on doit afficher le formulaire de login (aprÃ¨s inscription)
document.addEventListener('DOMContentLoaded', function() {
    if (container && container.classList.contains('active')) {
        // Le formulaire de login est dÃ©jÃ  affichÃ©
        toggleForm(false);
    }
    
    // Ajouter des effets de focus amÃ©liorÃ©s
    const inputs = document.querySelectorAll('.input-box input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'scale(1.02)';
            this.parentElement.style.transition = 'transform 0.3s ease';
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'scale(1)';
        });
    });
});

if (registerBtn) {
    registerBtn.addEventListener('click', (e) => {
        e.preventDefault();
        toggleForm(true);
    });
}

if (loginBtn) {
    loginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        toggleForm(false);
    });
}

// Face ID Support using WebAuthn API
let faceIdSupported = false;

// VÃ©rifier si WebAuthn est supportÃ©
if (window.PublicKeyCredential) {
    faceIdSupported = true;
    console.log('Face ID / WebAuthn est supportÃ©');
} else {
    console.log('Face ID / WebAuthn n\'est pas supportÃ© sur ce navigateur');
}

// Fonction pour enregistrer Face ID
async function registerFaceID() {
    if (!faceIdSupported) {
        alert('Face ID n\'est pas supportÃ© sur votre navigateur. Veuillez utiliser Chrome, Edge, Safari ou Firefox rÃ©cent.');
        return;
    }

    // VÃ©rifier que l'utilisateur est connectÃ©
    const csrftoken = getCookie('csrftoken');
    if (!csrftoken) {
        alert('Veuillez d\'abord vous inscrire ou vous connecter pour utiliser Face ID.');
        return;
    }

    try {
        const username = document.querySelector('.register input[name="username"]')?.value || 
                        document.querySelector('input[name="username"]')?.value || 
                        'user_' + Date.now();
        const email = document.querySelector('.register input[name="email"]')?.value || 
                     document.querySelector('input[name="email"]')?.value || 
                     '';

        // CrÃ©er un challenge simple (en production, utiliser un challenge serveur)
        const challenge = new Uint8Array(32);
        crypto.getRandomValues(challenge);

        // CrÃ©er le credential
        const publicKeyCredentialCreationOptions = {
            challenge: challenge,
            rp: {
                name: "GL Project",
                id: window.location.hostname,
            },
            user: {
                id: Uint8Array.from(username, c => c.charCodeAt(0)),
                name: email || username,
                displayName: username,
            },
            pubKeyCredParams: [{ alg: -7, type: "public-key" }],
            authenticatorSelection: {
                authenticatorAttachment: "platform",
                userVerification: "required"
            },
            timeout: 60000,
            attestation: "direct"
        };

        // Demander l'authentification biomÃ©trique
        const credential = await navigator.credentials.create({
            publicKey: publicKeyCredentialCreationOptions
        });

        // Encoder le credential ID en base64
        const credentialIdArray = new Uint8Array(credential.rawId);
        const credentialId = btoa(String.fromCharCode(...credentialIdArray));
        
        // Pour la clÃ© publique, on utilise l'attestation (simplifiÃ©)
        const publicKey = credentialId; // En production, extraire la vraie clÃ© publique
        
        const response = await fetch('/api/face-id/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                credentialId: credentialId,
                publicKey: publicKey
            })
        });

        const data = await response.json();
        if (data.success) {
            alert('Face ID enregistrÃ© avec succÃ¨s!');
        } else {
            alert('Erreur lors de l\'enregistrement: ' + (data.error || 'Erreur inconnue'));
        }
    } catch (error) {
        console.error('Erreur Face ID:', error);
        if (error.name === 'NotAllowedError') {
            alert('L\'authentification biomÃ©trique a Ã©tÃ© annulÃ©e ou refusÃ©e.');
        } else {
            alert('Erreur lors de l\'enregistrement Face ID: ' + error.message);
        }
    }
}

// Fonction pour authentifier avec Face ID
async function authenticateFaceID() {
    if (!faceIdSupported) {
        alert('Face ID n\'est pas supportÃ© sur votre navigateur.');
        return;
    }

    const username = document.querySelector('.login input[name="username"]')?.value;
    
    if (!username) {
        alert('Veuillez entrer votre nom d\'utilisateur ou email');
        return;
    }

    try {
        // CrÃ©er un challenge simple
        const challenge = new Uint8Array(32);
        crypto.getRandomValues(challenge);

        // Obtenir les credentials depuis le serveur
        const response = await fetch('/api/face-id/authenticate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                username: username
            })
        });

        const data = await response.json();
        
        if (data.credentialId) {
            // DÃ©coder le credential ID
            const credentialIdArray = Uint8Array.from(atob(data.credentialId), c => c.charCodeAt(0));
            
            // Authentifier avec le credential
            const publicKeyCredentialRequestOptions = {
                challenge: challenge,
                allowCredentials: [{
                    id: credentialIdArray,
                    type: 'public-key',
                    transports: ['internal']
                }],
                timeout: 60000,
                userVerification: "required"
            };

            const assertion = await navigator.credentials.get({
                publicKey: publicKeyCredentialRequestOptions
            });

            // Envoyer la vÃ©rification au serveur (simplifiÃ© - en production, vÃ©rifier la signature)
            const verifyResponse = await fetch('/api/face-id/authenticate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    credentialId: data.credentialId,
                    username: username
                })
            });

            const verifyData = await verifyResponse.json();
            if (verifyData.success) {
                window.location.href = verifyData.redirect || '/';
            } else {
                alert('Authentification Ã©chouÃ©e: ' + (verifyData.error || 'Erreur inconnue'));
            }
        } else {
            alert(data.error || 'Face ID non enregistrÃ© pour cet utilisateur');
        }
    } catch (error) {
        console.error('Erreur authentification Face ID:', error);
        if (error.name === 'NotAllowedError') {
            alert('L\'authentification biomÃ©trique a Ã©tÃ© annulÃ©e.');
        } else {
            alert('Erreur lors de l\'authentification Face ID: ' + error.message);
        }
    }
}

// Fonction helper pour obtenir le cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


// Ajouter les event listeners pour les boutons Face ID
document.addEventListener('DOMContentLoaded', function() {
    const faceIdRegisterBtn = document.getElementById('faceIdRegisterBtn');
    const faceIdLoginBtn = document.getElementById('faceIdLoginBtn');
    
    if (faceIdRegisterBtn) {
        faceIdRegisterBtn.addEventListener('click', registerFaceID);
    }
    
    if (faceIdLoginBtn) {
        faceIdLoginBtn.addEventListener('click', authenticateFaceID);
    }
});

// --- Enhancements: staggered entrance for panels ---
(function(){
  function animateStagger(scopeSelector){
    const scope = document.querySelector(scopeSelector);
    if (!scope) return;
    const elems = scope.querySelectorAll('h1, .input-box, .btn, .social-icons');
    elems.forEach((el,i)=>{
      el.classList.add('stagger-enter');
      void el.offsetWidth;
      setTimeout(()=>el.classList.add('stagger-enter-active'), 60 + i*60);
      setTimeout(()=>el.classList.remove('stagger-enter','stagger-enter-active'), 900 + i*60);
    });
  }
  document.addEventListener('DOMContentLoaded', function(){
    const containerEl = document.querySelector('.container');
    if (!containerEl) return;
    animateStagger(containerEl.classList.contains('active') ? '.form-box.register' : '.form-box.login');
  });
  if (registerBtn){
    registerBtn.addEventListener('click', ()=> setTimeout(()=> animateStagger('.form-box.register'), 120));
  }
  if (loginBtn){
    loginBtn.addEventListener('click', ()=> setTimeout(()=> animateStagger('.form-box.login'), 120));
  }
})();


