const { ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

module.exports = () => {
    const r1 = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId('seek_back').setEmoji('⏪').setStyle(ButtonStyle.Secondary),
        new ButtonBuilder().setCustomId('pause_resume').setEmoji('⏯️').setStyle(ButtonStyle.Success),
        new ButtonBuilder().setCustomId('stop').setEmoji('⏹️').setStyle(ButtonStyle.Danger),
        new ButtonBuilder().setCustomId('seek_fwd').setEmoji('⏩').setStyle(ButtonStyle.Secondary)
    );
    const r2 = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId('prev').setEmoji('⏮️').setStyle(ButtonStyle.Primary),
        new ButtonBuilder().setCustomId('queue').setEmoji('📜').setStyle(ButtonStyle.Secondary),
        new ButtonBuilder().setCustomId('add_song').setEmoji('➕').setStyle(ButtonStyle.Success).setLabel("Add Song"),
        new ButtonBuilder().setCustomId('skip').setEmoji('⏭️').setStyle(ButtonStyle.Primary)
    );
    const r3 = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId('vol_down').setEmoji('🔉').setStyle(ButtonStyle.Secondary),
        new ButtonBuilder().setCustomId('mute').setEmoji('🔇').setStyle(ButtonStyle.Danger),
        new ButtonBuilder().setCustomId('vol_up').setEmoji('🔊').setStyle(ButtonStyle.Secondary)
    );
    return [r1, r2, r3];
};