use base64::{engine::general_purpose::STANDARD_NO_PAD as b64, Engine as _};
use ring::{
    digest::{digest, SHA384},
    rand::{SecureRandom as _, SystemRandom},
};
use std::env;
use std::net::TcpListener;
use std::sync::Arc;
use std::thread::spawn;
use tungstenite::{accept, Message};

fn retrieve_secret() -> String {
    env::var("SECRET_SECRET").unwrap().trim().to_owned()
}

fn main() {
    let server = TcpListener::bind("0.0.0.0:80").unwrap();
    let sysrand = Arc::new(SystemRandom::new());
    for stream in server.incoming() {
        let sysrand_ref = sysrand.clone();
        spawn(move || {
            println!("Accepting connection...");
            if let Ok(mut websocket) = accept(stream.unwrap()) {
                println!("Connected, creating challenge...");
                let mut challenge = [0_u8; 32];
                sysrand_ref.fill(&mut challenge).unwrap();
                let challenge_b64 = b64.encode(challenge);
                let challenge_msg = format!("c{}", challenge_b64);
                println!("Created, computing response...");
                let mut owned_combined = retrieve_secret();
                owned_combined.push_str(&challenge_b64);
                let resp_exp = digest(&SHA384, &owned_combined.into_bytes());
                let resp_exp_b64 = b64.encode(resp_exp);
                println!("Computed, sending challenge...");
                websocket.send(Message::Text(challenge_msg)).unwrap();
                println!("Sent, entering send/receive loop...");
                let mut responded = false;
                'sendrecv: while let Ok(msg) = websocket.read() {
                    if msg.is_text() {
                        let text = msg.to_text().unwrap();
                        match text.chars().nth(0) {
                            Some('r') => {
                                if &resp_exp_b64 == &text[1..] {
                                    println!("Got valid response, ready for data transfer :)");
                                    responded = true;
                                } else {
                                    println!("Got bad response: {:?}", &text[1..]);
                                    println!("Got bad response, breaking out of loop :(");
                                    break 'sendrecv;
                                }
                            }
                            Some('d') => {
                                if !responded {
                                    println!("Got data before response, breaking out of loop :(");
                                    break 'sendrecv;
                                }
                                let data = &text[1..];
                                println!(">>> MESSAGE: {} <<<", data);
                            }
                            _ => {}
                        }
                    }
                }
            }
        });
    }
}
