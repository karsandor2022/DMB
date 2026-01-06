const { Events, ModalBuilder, TextInputBuilder, TextInputStyle, ActionRowBuilder } = require('discord.js');
const getProgressBar = require('../utils/progressbar');
const playCommand = require('../commands/music/play'); // Point to play.js

module.exports = {
    name: Events.InteractionCreate,
    async execute(client, interaction) {
        
        // 1. COMMANDS
        if (interaction.isChatInputCommand()) {
            const command = client.commands.get(interaction.commandName);
            if (command) await command.execute(client, interaction);
        }

        // 2. MODAL (ADD SONG)
        if (interaction.isModalSubmit() && interaction.customId === 'add_song_modal') {
            await playCommand.execute(client, interaction);
        }

        // 3. BUTTONS
        if (interaction.isButton()) {
            const action = interaction.customId;

            if (action === 'add_song') {
                const modal = new ModalBuilder().setCustomId('add_song_modal').setTitle('Add Song');
                const input = new TextInputBuilder().setCustomId('song_input').setLabel("URL or Name").setStyle(TextInputStyle.Short);
                modal.addComponents(new ActionRowBuilder().addComponents(input));
                return await interaction.showModal(modal);
            }

            await interaction.deferUpdate();

            if (client.mode === 'LOCAL') {
                const queue = client.player.nodes.get(interaction.guild.id);
                if (!queue) return;

                switch (action) {
                    case 'pause_resume': queue.node.isPaused() ? queue.node.resume() : queue.node.pause(); break;
                    case 'stop': queue.delete(); break;
                    case 'skip': queue.node.skip(); break;
                    case 'prev': if (queue.history.previousTrack) queue.history.back(); break;
                    case 'seek_fwd': queue.node.seek(queue.node.streamTime + 10000); break;
                    case 'seek_back': queue.node.seek(queue.node.streamTime - 10000); break;
                    case 'vol_up': queue.node.setVolume(Math.min(queue.node.volume + 10, 100)); break;
                    case 'vol_down': queue.node.setVolume(Math.max(queue.node.volume - 10, 0)); break;
                    case 'mute': queue.node.setVolume(queue.node.volume === 0 ? 50 : 0); break;
                    case 'queue': 
                        const t = queue.tracks.map((t, i) => `${i+1}. ${t.title}`).join('\n').substring(0, 1000);
                        interaction.followUp({ content: `📜 **Queue:**\n${t || 'Empty'}`, ephemeral: true });
                        break;
                }
                
                // Update Progress Bar
                if (queue.currentTrack) {
                    const bar = getProgressBar(queue.node.streamTime, queue.currentTrack.durationMS);
                    await interaction.message.edit({
                        content: `🎵 **Playing (Local):** ${queue.currentTrack.title}\n${bar}`
                    });
                }
            } else {
                // Remote logic similar to above (simplified for brevity)
                const node = client.shoukaku.getNode();
                const player = node.players.get(interaction.guild.id);
                if (player && action === 'stop') {
                     player.stopTrack(); 
                     client.shoukaku.leaveVoiceChannel(interaction.guild.id);
                }
            }
        }
    }
};