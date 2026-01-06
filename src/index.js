require('dotenv').config();
const { Client, GatewayIntentBits, Collection } = require('discord.js');
const { Player } = require('discord-player');
const { DefaultExtractors } = require('@discord-player/extractor');
const { YoutubeiExtractor } = require("discord-player-youtubei");
const { Shoukaku, Connectors } = require('shoukaku');
const fs = require('fs');
const path = require('path');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

client.commands = new Collection();
client.mode = process.env.NODE_ENV === 'remote' ? 'REMOTE' : 'LOCAL';
client.defaultVolume = 50; // Default base volume

// --- LOAD COMMANDS (Recursive) ---
const loadCommands = (dir) => {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const fullPath = path.join(dir, file);
        if (fs.lstatSync(fullPath).isDirectory()) {
            loadCommands(fullPath);
        } else if (file.endsWith('.js')) {
            const command = require(fullPath);
            client.commands.set(command.name, command);
            console.log(`✅ Command Loaded: ${command.name}`);
        }
    }
};
loadCommands(path.join(__dirname, 'commands'));

// --- LOAD EVENTS ---
const eventsPath = path.join(__dirname, 'events');
if (fs.existsSync(eventsPath)) {
    const eventFiles = fs.readdirSync(eventsPath).filter(file => file.endsWith('.js'));
    for (const file of eventFiles) {
        const event = require(path.join(eventsPath, file));
        client.on(event.name, (...args) => event.execute(client, ...args));
    }
}

// --- SETUP AUDIO ENGINE ---
async function setupAudio() {
    if (client.mode === 'LOCAL') {
        console.log("🟢 [System] Loading LOCAL Engine (InnerTube)...");
        client.player = new Player(client);
        
        // Android Bypass for 18+ (The 'Muse' Method)
        await client.player.extractors.register(YoutubeiExtractor, {
            streamOptions: { useClient: "ANDROID" }
        });
        
        await client.player.extractors.loadMulti(DefaultExtractors);
        console.log("✅ [System] Local Engine Ready");
    } else {
        console.log("🔵 [System] Loading REMOTE Engine (Lavalink)...");
        const Nodes = [{
            name: process.env.LAVALINK_NAME || 'Node1',
            url: process.env.LAVALINK_URL,
            auth: process.env.LAVALINK_AUTH
        }];
        client.shoukaku = new Shoukaku(new Connectors.DiscordJS(client), Nodes);
        client.shoukaku.on('error', (_, error) => console.error('Lavalink Error:', error));
        client.shoukaku.on('ready', (name) => console.log(`✅ [System] Lavalink ${name} Ready`));
    }
}

client.once('ready', async () => {
    await setupAudio();
    console.log(`🤖 Logged in as ${client.user.tag}`);
    // Register commands globally
    const data = client.commands.map(c => ({ name: c.name, description: c.description, options: c.options }));
    await client.application.commands.set(data);
});

client.login(process.env.DISCORD_TOKEN);