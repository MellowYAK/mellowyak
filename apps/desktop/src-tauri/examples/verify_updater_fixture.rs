use minisign_verify::{PublicKey, Signature};
use std::{env, fs, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 4 {
        return Err("usage: verify_updater_fixture <public-key> <signature> <artifact>".into());
    }
    let public_key = PublicKey::decode(&fs::read_to_string(Path::new(&arguments[1]))?)?;
    let signature = Signature::decode(&fs::read_to_string(Path::new(&arguments[2]))?)?;
    let artifact = fs::read(Path::new(&arguments[3]))?;
    public_key.verify(&artifact, &signature, true)?;
    println!("VERIFIED");
    Ok(())
}
